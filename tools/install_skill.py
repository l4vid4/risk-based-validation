"""Copy the portable skill without overwriting an existing destination."""
import argparse
from pathlib import Path
import shutil


def install(target):
    source = Path(__file__).resolve().parents[1] / 'skills/risk-based-validation'
    destination = Path(target).expanduser().resolve() / source.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f'Already exists; inspect before updating: {destination}')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, help='Agent skill parent directory, e.g. /repo/.agents/skills')
    args = parser.parse_args()
    try:
        print(install(args.target))
    except (OSError, shutil.Error) as e:
        parser.exit(2, f'{e}\n')


if __name__ == '__main__':
    main()
