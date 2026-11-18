"""CLI. Local offline demonstration relies on tests; live mode needs network."""
import argparse
from datetime import datetime,timezone
import json
import sys
from pathlib import Path
from .pipeline import update
from .provider import SourceError
from .store import load
from .doctor import audit,format_report

def main(argv=None):
    parser=argparse.ArgumentParser(description="Basketball AI Lab: NBA key-free")
    sub=parser.add_subparsers(dest="cmd",required=True)
    run=sub.add_parser("update",help="Ingest ESPN and archive actual prospective picks")
    run.add_argument("--output",type=Path,default=Path("data"))
    run.add_argument("--site",type=Path,default=Path("site/data"))
    status=sub.add_parser("status",help="Show archived health state without network")
    status.add_argument("--output",type=Path,default=Path("data"))
    doctor=sub.add_parser("doctor",help="Auditar archivo y escudos sin red ni modificaciones")
    doctor.add_argument("--output",type=Path,default=Path("data"))
    doctor.add_argument("--site",type=Path,default=Path("site/data"))
    doctor.add_argument("--require-live",action="store_true")
    doctor.add_argument("--json",action="store_true")
    opts=parser.parse_args(argv)
    if opts.cmd=="doctor":
        report=audit(opts.output,opts.site,require_live=opts.require_live)
        print(json.dumps(report,ensure_ascii=False,indent=2) if opts.json else format_report(report))
        return 2 if report["state"]=="ERROR" else 0
    if opts.cmd=="status":
        print(json.dumps(load(opts.output/"status.json",{}),ensure_ascii=False,indent=2));return 0
    try:
        report=update(opts.output,opts.site)
        print(json.dumps({k:v for k,v in report.items() if k not in ("no_top3_reasons",)},
            ensure_ascii=False,indent=2))
        return 0
    except SourceError as exc:
        print("Fuente no disponible; no se alteró el archivo: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":sys.exit(main())
