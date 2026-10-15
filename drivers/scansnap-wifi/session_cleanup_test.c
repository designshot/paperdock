/* SPDX-License-Identifier: GPL-2.0-or-later WITH SANE-exception */
/* Local offline replay of the production reservation and cleanup code. */
#include <arpa/inet.h>
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netpacket/packet.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { \
  fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expr); exit(1); \
} } while (0)

typedef struct {
  unsigned char incoming[128], outgoing[256];
  size_t length, offset, written;
  int closed, fail_write_after;
} Replay;
static Replay replay[8];
static int socket_count;

static int mock_socket(int domain, int type, int protocol)
{
  (void)domain; (void)type; (void)protocol;
  CHECK(socket_count < 8);
  return 100 + socket_count++;
}
static Replay *connection(int fd) { CHECK(fd >= 100 && fd < 108); return replay + fd - 100; }
static int mock_bind(int fd, const struct sockaddr *address, socklen_t length)
{ (void)connection(fd); (void)address; (void)length; return 0; }
static int mock_connect(int fd, const struct sockaddr *address, socklen_t length)
{ (void)connection(fd); (void)address; (void)length; return 0; }
static int mock_setsockopt(int fd, int level, int name, const void *value, socklen_t length)
{ (void)connection(fd); (void)level; (void)name; (void)value; (void)length; return 0; }
static int mock_close(int fd) { connection(fd)->closed = 1; return 0; }
static ssize_t mock_recv(int fd, void *buffer, size_t length, int flags)
{
  Replay *item = connection(fd);
  size_t available = item->length - item->offset;
  (void)flags;
  if (!available) { errno = ETIMEDOUT; return -1; }
  if (length > available) length = available;
  if (length > 3) length = 3;
  memcpy(buffer, item->incoming + item->offset, length);
  item->offset += length;
  return (ssize_t)length;
}
static ssize_t mock_send(int fd, const void *buffer, size_t length, int flags)
{
  Replay *item = connection(fd);
  (void)flags;
  if (item->fail_write_after >= 0 && item->written >= (size_t)item->fail_write_after)
    { errno = ECONNRESET; return -1; }
  if (length > 7) length = 7;
  CHECK(item->written + length <= sizeof(item->outgoing));
  memcpy(item->outgoing + item->written, buffer, length);
  item->written += length;
  return (ssize_t)length;
}

#define socket mock_socket
#define bind mock_bind
#define connect mock_connect
#define setsockopt mock_setsockopt
#define close mock_close
#define recv mock_recv
#define send mock_send
#include "scansnap-protocol.c"
#undef socket
#undef bind
#undef connect
#undef setsockopt
#undef close
#undef recv
#undef send

static SsDevice device;
static SsSession session;
static char error[256];

static void frame(int index, unsigned int length, int status)
{
  Replay *item = replay + index;
  unsigned char *p = item->incoming + item->length;
  CHECK(item->length + length <= sizeof(item->incoming));
  memset(p, 0, length);
  put_be32(p, length); memcpy(p + 4, "VENS", 4);
  put_be32(p + 8, (uint32_t)status);
  if (length == 20) put_be16(p + 12, 16);
  item->length += length;
}
static void reset(void)
{
  int i;
  memset(replay, 0, sizeof(replay)); socket_count = 0;
  for (i = 0; i < 8; i++) replay[i].fail_write_after = -1;
  memset(&device, 0, sizeof(device)); memset(&session, 0, sizeof(session));
  strcpy(device.ip, "192.0.2.20");
  memcpy(device.magic, "VENS", 4);
  memcpy(device.identity, "\x00\x11\x22\x33\x44\x55", 6);
  memcpy(device.local_ip, "\xc0\x00\x02\x0a", 4);
  device.application_port = 53219; device.scanner_port = 53218;
  error[0] = 0;
}
static void release_reply(int index) { frame(index, 16, 0); frame(index, 16, 0); }
static void check_release(int index)
{
  Replay *item = replay + index;
  CHECK(item->written == 32);
  CHECK(get_be32(item->outgoing + 8) == 18);
  CHECK(!memcmp(item->outgoing + 16, device.identity, 6));
  CHECK(get_be32(item->outgoing + 24) == 0);
  CHECK(get_be32(item->outgoing + 28) == 0);
  CHECK(item->closed && replay[0].closed);
  CHECK(session.reserved == 0 && session.trigger_fd == -1);
}

int main(void)
{
  time_t now;
  struct tm local;
  reset(); frame(1, 16, 0); release_reply(2);
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(replay[1].written == 128); check_release(2);

  reset(); frame(1, 16, 0); frame(1, 20, -4);
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(socket_count == 2 && replay[0].closed && replay[1].closed);
  CHECK(strstr(error, "command 17") && strstr(error, "status -4"));

  reset(); frame(1, 16, 0); frame(1, 20, 0);
  replay[1].incoming[20] = 'X'; release_reply(2);
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(strstr(error, "framing")); check_release(2);

  reset(); frame(1, 16, 0); replay[1].fail_write_after = 7; release_reply(2);
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(replay[1].written == 7); check_release(2);

  reset(); /* Greeting timeout happens before reservation is sent. */
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(socket_count == 2 && replay[1].written == 0);
  CHECK(replay[0].closed && session.reserved == 0);

  reset(); frame(1, 16, 0); frame(1, 20, 0); release_reply(3);
  CHECK(ss_session_open(&session, &device, error, sizeof(error)) == -1);
  CHECK(replay[2].written == 0); check_release(3);
  now = time(NULL); CHECK(localtime_r(&now, &local) != NULL);
  CHECK((int32_t)get_be32(replay[1].outgoing + 116) == -(long)local.tm_gmtoff);

  puts("ScanSnap: 6 offline reservation/cleanup cases passed; normal release only");
  return 0;
}
