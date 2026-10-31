"""Run a fixed-account task without exposing credentials to the AI caller."""
import argparse
import json
from pathlib import Path
from community_client import CommunityClient, DOMAINS, CommunityError
from community_reads import CommunityReads
from session_store import SessionStore
from community_actions import CommunityActions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=DOMAINS, default=DOMAINS[0])
    parser.add_argument('--account', help='Saved account ID; required for account tasks')
    parser.add_argument('--anonymous', action='store_true', help='Public reads only')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('accounts')
    commands.add_parser('forget')
    tags = commands.add_parser('tags')
    tags.add_argument('--category', choices=['Experiment', 'Discussion', 'Model'])
    for name, key in [('comments', 'targets'), ('works', 'queries')]:
        p = commands.add_parser(name)
        p.add_argument('--input', type=Path, required=True, help=f'JSON array of {key}')
    batch = commands.add_parser('batch')
    batch.add_argument('--input', type=Path, required=True,
                       help='JSON object: path, bodies, write (explicit task authorization required)')
    inspect = commands.add_parser('inspect')
    inspect.add_argument('content_ids', nargs='+')
    inspect.add_argument('--output-dir', type=Path, required=True)
    publish = commands.add_parser('publish')
    publish.add_argument('--archive', type=Path, required=True)
    publish.add_argument('--title')
    publish.add_argument('--description')
    publish.add_argument('--tag', action='append')
    publish.add_argument('--category', choices=['Experiment','Discussion','Model'], default='Experiment')
    publish.add_argument('--cover', type=Path)
    avatar = commands.add_parser('avatar')
    avatar.add_argument('--image', type=Path, required=True)
    cover = commands.add_parser('cover')
    cover.add_argument('--summary-id', required=True)
    cover.add_argument('--category', default='Experiment')
    cover.add_argument('--image', type=Path, required=True)
    remove = commands.add_parser('remove')
    remove.add_argument('--summary-id', required=True)
    remove.add_argument('--category', default='Experiment')
    remove.add_argument('--mode', choices=['delete','hide','restore'], required=True)
    remove.add_argument('--reason', default='')
    actions_parser = commands.add_parser('actions')
    actions_parser.add_argument('--input', type=Path, required=True)
    for name in ('featured','knowledge'):
        command=commands.add_parser(name)
        command.add_argument('--summary-id',action='append',required=True,help='Repeat for up to 20 works')
        command.add_argument('--status',choices=['add','remove'],required=True)
        command.add_argument('--category',choices=['Experiment','Discussion','Model'],default='Experiment')
    args = parser.parse_args()
    try:
        if args.command in ('accounts', 'forget'):
            store = SessionStore()
            if args.command == 'accounts':
                result = store.accounts()
            else:
                if not args.account:
                    parser.error('--account is required')
                store.forget(args.domain, args.account)
                result = {'removed': args.account, 'domain': args.domain}
        else:
            if args.anonymous and args.account:
                parser.error('Choose --account or --anonymous')
            if args.anonymous and args.command in ('publish','avatar','cover','remove','actions','featured','knowledge'):
                parser.error('This command requires --account')
            if args.anonymous:
                api = CommunityClient(domain=args.domain)
                api.login()
            elif args.account:
                api = CommunityClient.from_saved(args.account, domain=args.domain)
            else:
                parser.error('Choose --account or --anonymous; use login_gui.py to add accounts')
            client = CommunityReads(api.request)
            actions = CommunityActions(api)
            if args.command == 'tags':
                result = client.get_available_tags(args.category)
            elif args.command == 'inspect':
                result = client.inspect_experiments(args.content_ids, args.output_dir)
            elif args.command == 'publish':
                result = actions.publish(args.archive,title=args.title,description=args.description,tags=args.tag,category=args.category,cover=args.cover)
            elif args.command == 'avatar':
                result = actions.set_avatar(args.image)
            elif args.command == 'cover':
                result = actions.set_cover(args.summary_id,args.image,category=args.category)
            elif args.command == 'remove':
                result = actions.restore(args.summary_id,category=args.category,reason=args.reason) if args.mode=='restore' else actions.remove(args.summary_id,category=args.category,hide=args.mode=='hide',reason=args.reason)
            elif args.command == 'actions':
                result = actions.run_batch(json.loads(args.input.read_text(encoding='utf-8-sig')))
            elif args.command in ('featured','knowledge'):
                method=actions.set_featured_batch if args.command=='featured' else actions.set_knowledge_base_batch
                result=method(args.summary_id,args.status=='add',args.category)
            else:
                if args.input.stat().st_size > 1048576:
                    raise ValueError('Task input exceeds 1MB; never put saved experiments in this file')
                body = json.loads(args.input.read_text(encoding='utf-8-sig'))
                if args.command == 'comments':
                    result = client.fetch_comments_batch(body)
                elif args.command == 'works':
                    result = client.fetch_works_batch(body)
                else:
                    if args.anonymous and body.get('write'):
                        raise ValueError('Anonymous mode does not support state-changing tasks')
                    result = client.call_batch(**body)
        print(json.dumps(result, ensure_ascii=False))
    except CommunityError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False))
        return 1
    except Exception as error:
        print(json.dumps({'ok': False, 'errorType': type(error).__name__}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
