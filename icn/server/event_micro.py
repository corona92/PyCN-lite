# pycn-lite/icn/lib/event_micro.py

# (c) 2018-02-05 <christian.tschudin@unibas.ch>

# the event loop for Micropython

import uselect
import usocket
import utime

# ---------------------------------------------------------------------------

class Loop():

    def __init__(self):
        self.time_dict = {}
        self.sock_list = []
        self.p = uselect.poll()

    def register_timer(self, cb, delta, arg):
        self.time_dict[cb] = [utime.ticks_ms(), int(delta*1000), arg]

    def udp_open(self, addr, recv_cb, send_done_cb, arg):
        # recv_cb MUST be set
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        addr = usocket.getaddrinfo(addr[0], addr[1])[0][-1]
        s.bind(addr)
        if send_done_cb:
            s.setblocking(False)
        self.sock_list.append([s, recv_cb, send_done_cb, arg])
        self.p.register(s, uselect.POLLIN)
        return s

    def udp_sendto(self, s, buf, addr):
        s.sendto(buf, addr)
        for cb in self.sock_list:
            if cb[0] == s and cb[2]:
                self.p.register(s, uselect.POLLIN | uselect.POLLOUT)

    def udp_close(self, s):
        rm = None
        for i in range(len(self.sock_list)):
            if self.sock_list[i][0] == s:
                self.p.unregister(s)
                rm = i
                break
        if rm != None:
            del self.sock_list[i]

    def forever(self):
        while True:
            now = utime.ticks_ms()
            tout = None
            for cb in self.time_dict:
                d = utime.ticks_diff(self.time_dict[cb][0], now)
                if d < 0:
                    cb(self, self.time_dict[cb][2])
                    d = self.time_dict[cb][1]
                    self.time_dict[cb][0] = utime.ticks_add(now, d)
                if tout == None or d < tout:
                    tout = d
            ok = self.p.poll(tout)
            for s in ok:
                e = s[1]
                s = s[0]
                for cb in self.sock_list:
                    if (e & uselect.POLLIN) and cb[0] == s:
                        cb[1](self, s, cb[3])
                    elif (e & uselect.POLLOUT) and cb[0] == s:
                        self.p.register(s, uselect.POLLIN)
                        if cb[2]:
                            cb[2](self, s, cb[3])

# eof
