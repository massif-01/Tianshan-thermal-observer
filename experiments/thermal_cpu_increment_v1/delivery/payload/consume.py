"""File replay or explicitly enabled loopback ingress; never polls a device or issues work."""
import argparse
import datetime as dt
import ipaddress
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from common import ROOT, lines, jsonl
from activity import load_candidate, Processor


def make_server(processor, *, allow_loopback, host='127.0.0.1', port=0, max_frames=10000):
    if not allow_loopback:
        raise PermissionError('explicit loopback-service permission required')
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError('research ingress binds loopback only; no device listener')
    clock_id='consumer-monotonic:'+str(time.monotonic_ns())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != '/observe':
                self.send_error(404)
                return
            try:
                length=int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1024*1024:
                    raise ValueError('frame size outside interface budget')
                frame=json.loads(self.rfile.read(length))
                # An actual receiver stamps arrival. It never claims a source-only file
                # arrived at its historical source time. Producer deadlines must already
                # be in this host monotonic domain; unknown clocks remain unavailable.
                stamp=time.monotonic()
                frame['ingress_received_mono_s']=stamp
                frame['ingress_received_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
                frame['producer_declared_arrival_mono_s']=frame.get('arrival_mono_s')
                if frame.get('ingress_clock_id') == 'local_monotonic_current_boot':
                    frame['arrival_mono_s']=stamp
                    frame['arrival_clock_id']=clock_id
                    frame['source_only']=False
                    for f in frame.get('features',{}).values():
                        f['available_at_mono_s']=max(stamp,f.get('available_at_mono_s',stamp))
                else:
                    frame['arrival_mono_s']=stamp
                    frame['arrival_clock_id']=None
                    frame['source_only']=True
                if self.server.frames >= max_frames:
                    raise ValueError('finite ingress frame budget exhausted')
                self.server.frames += 1
                result=processor.process(frame)
                result['ingress_received_mono_s']=stamp
                payload=json.dumps(result,ensure_ascii=False,allow_nan=False).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (ValueError,TypeError,KeyError) as e:
                self.send_error(400,str(e))

    server=HTTPServer((host,port),Handler)
    server.frames=0
    return server


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    r=sub.add_parser('replay')
    r.add_argument('--input',type=str,required=True)
    r.add_argument('--output',type=str,required=True)
    s=sub.add_parser('serve')
    s.add_argument('--allow-loopback-service',action='store_true')
    s.add_argument('--port',type=int,default=0)
    s.add_argument('--duration-s',type=float,default=60.)
    args=ap.parse_args()
    c,f=load_candidate()
    processor=Processor(c,f)
    if args.command=='replay':
        from pathlib import Path
        out=Path(args.output)
        if out.exists():
            raise FileExistsError('use a new output path')
        jsonl(out,(processor.process(frame) for frame in lines(args.input)))
    else:
        if not 0 < args.duration_s <= 1200:
            raise ValueError('finite duration must be <=1200s')
        server=make_server(processor,allow_loopback=args.allow_loopback_service,port=args.port)
        server.timeout=.2
        deadline=time.monotonic()+args.duration_s
        print(json.dumps(dict(loopback=server.server_address,deadline_mono_s=deadline,device_clients=0)),flush=True)
        try:
            while time.monotonic()<deadline:
                server.handle_request()
        finally:
            server.server_close()


if __name__=='__main__':
    main()
