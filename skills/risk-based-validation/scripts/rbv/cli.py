"""Agent-friendly JSON CLI. Plan is read-only; run requires explicit execution intent."""
import argparse
import json
import sys

from . import __version__
from .config import ValidationError
from .planner import make_plan
from .runner import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('plan', 'run'):
        p = sub.add_parser(action)
        p.add_argument('--repo', default='.', help='Git root (not a subdirectory)')
        p.add_argument('--config', default='.rbv.json')
        p.add_argument('--base', default='HEAD', help='Use a reviewed merge-base commit for PRs; HEAD means local changes only')
        p.add_argument('--full', action='store_true', help='Select the complete registered inventory')
        if action == 'run':
            p.add_argument('--execute', action='store_true', help='Execute reviewed repository commands in the current sandbox')
            p.add_argument('--context', help='Caller-managed dependency/toolchain/external-state identity; required for opt-in reuse')
            p.add_argument('--budget', type=float, help='Wall seconds; exhaustion is incomplete, never success')
            p.add_argument('--no-cache', action='store_true')
            p.add_argument('--cache-ttl', type=float, default=3600, help='Maximum reuse age in seconds, at most 86400')
    args = parser.parse_args(argv)
    try:
        if args.action == 'plan':
            value = make_plan(args.repo, args.config, args.base, args.full)
            value.pop('config')
            code = 2 if value['blockers'] else 0
        else:
            if not args.execute:
                raise ValidationError('run requires --execute after reviewing commands; plan never executes tests')
            value = run(args.repo, args.config, args.base, context=args.context, budget=args.budget,
                        no_cache=args.no_cache, full=args.full, ttl=args.cache_ttl)
            code = 0 if value['status'] in ('passed', 'no_checks_required') else (1 if value['status'] == 'failed' else 2)
        print(json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False))
        return code
    except (ValidationError, OSError, ValueError) as e:
        print(json.dumps({'status': 'error', 'error': str(e)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
