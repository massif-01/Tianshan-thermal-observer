import argparse
import asyncio
import json
import logging
import os
import signal
import socket
import sys
from pathlib import Path
from aiohttp import web
from .common import load
from .server import app_for, configuration
from .source import Publication


def main():
    # Tiny frozen matrices need one numerical worker, preserving N305 cores for applications.
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        os.environ[name]='1'
    parser=argparse.ArgumentParser(description='TTO只读热观察台，固定59009')
    sub=parser.add_subparsers(dest='command',required=True)
    serve=sub.add_parser('serve');serve.add_argument('--config',required=True)
    field=sub.add_parser('publish-field',help='Run existing authorized field entry with one public follow hook')
    field.add_argument('--config',required=True);field.add_argument('--binding',required=True);field.add_argument('--output',required=True)
    field.add_argument('--descriptor',required=True);field.add_argument('--mode',choices=['diagnose','execute'],required=True);field.add_argument('--duration',type=float,default=300)
    template=sub.add_parser('field-template',help='Generate unapproved field binding for explicit host-side review')
    template.add_argument('--config',required=True);template.add_argument('--mode',choices=['diagnose','execute'],required=True);template.add_argument('--output',required=True)
    args=parser.parse_args()
    # Source data, secrets, URLs and exception bodies never enter HTTP access logs.
    logging.basicConfig(level=logging.ERROR)
    try:
        if args.command=='serve':
            c=configuration(args.config)
            # Reserve the port before startup can create an observe transport.
            family=socket.AF_INET6 if ':' in c['web']['bind'] else socket.AF_INET
            sock=socket.socket(family,socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try:
                sock.bind((c['web']['bind'],59009));sock.listen(128);sock.setblocking(False)
                web.run_app(app_for(c),sock=sock,access_log=None,print=None,shutdown_timeout=5.)
            finally:sock.close()
        elif args.command=='field-template':
            from tto.config import load_config
            from tto_field.cli import preview
            output=Path(args.output)
            if output.exists():raise ValueError('binding output already exists')
            output.write_text(json.dumps(preview(load_config(args.config,environ={}),args.mode),ensure_ascii=False,indent=2)+'\n');output.chmod(0o600)
        else:
            from tto.config import load_config
            from tto_field.runtime import run
            async def launch():
                async with Publication(args.descriptor) as publication:
                    await run(load_config(args.config,environ={}),load(args.binding),args.mode,Path(args.output),duration=args.duration,public_sink=publication.put)
            asyncio.run(launch())
    except OSError as e:
        print('Web启动失败：59009端口或本地资源不可用；未停止其他进程。',file=sys.stderr);raise SystemExit(2)
    except ValueError:
        print('配置/拥有权校验失败；请核对本地配置，未连接新的来源。',file=sys.stderr);raise SystemExit(2)


if __name__=='__main__':main()
