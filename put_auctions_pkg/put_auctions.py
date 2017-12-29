# TODO: It is completed only for 'insider' auctions

# HOW TO USE:
# ./put_auctions.py insider planning
# ./put_auctions.py insider run
# ./put_auctions.py insider load-testing 10000

import os
import os.path
import os.path
import json
import argparse
import contextlib
import tempfile
from dateutil.tz import tzlocal
from subprocess import check_output
from datetime import datetime, timedelta
from math import ceil, log10

PAUSE_SECONDS = timedelta(seconds=120)
PWD = os.path.dirname(os.path.realpath(__file__))
CWD = os.getcwd()

TENDER_DATA = \
    {'insider': {'path': 'src/openprocurement.auction.insider/openprocurement/auction/insider/tests/functional/data/tender_insider.json',
                 'worker': 'auction_insider',
                 'id': 'NOT DEFINED YET',
                 'config': 'auction_worker_insider.yaml',
                 'tender_id_base': '1'}}


@contextlib.contextmanager
def update_auctionPeriod(path, auction_type):
    with open(path) as file:
        data = json.loads(file.read())
    new_start_time = (datetime.now(tzlocal()) + PAUSE_SECONDS).isoformat()

    if auction_type == 'simple':
        data['data']['auctionPeriod']['startDate'] = new_start_time
    elif auction_type == 'multilot':
        for lot in data['data']['lots']:
            lot['auctionPeriod']['startDate'] = new_start_time

    with tempfile.NamedTemporaryFile(delete=False) as auction_file:
        json.dump(data, auction_file)
        auction_file.seek(0)
    yield auction_file.name
    auction_file.close()


def planning(tender_file_path, worker, auction_id, config):
    with update_auctionPeriod(tender_file_path,
                              auction_type='simple') as auction_file:
        os.system('{0}/bin/{1} planning {2}'
                  ' {0}/etc/{3} --planning_procerude partial_db --auction_info {3}'.format(
            CWD, worker, auction_id, config, auction_file))
    os.system('sleep 3')


def run(tender_file_path, worker, auction_id, config):
    with update_auctionPeriod(tender_file_path,
                              auction_type='simple') as auction_file:
        check_output('{0}/bin/{1} run {2}'
                     ' {0}/etc/{3} --planning_procerude partial_db --auction_info {3}'.format(
            CWD, worker, auction_id, config, auction_file).split())
    os.system('sleep 3')


def load_testing(tender_file_path, worker, config, count, tender_id_base):
    positions = int(ceil(log10(count)))

    for i in xrange(0, count):
        auction_id_template = \
            tender_id_base * (32 - positions) + '{{0:0{}d}}'.format(positions)

        auction_id = auction_id_template.format(i)
        planning(tender_file_path, worker, auction_id, config)
        # run(tender_file_path, worker, auction_id, config)


def main(auction_type, action_type, auctions_count=0):
    actions = globals()
    if action_type in actions:
        if action_type == 'load-testing':
            load_testing(
                TENDER_DATA[auction_type]['path'],
                TENDER_DATA[auction_type]['worker'],
                TENDER_DATA[auction_type]['config'],
                auctions_count,
                TENDER_DATA[auction_type]['tender_id_base'],
            )
        else:
            actions.get(action_type)(TENDER_DATA[auction_type]['path'],
                                     TENDER_DATA[auction_type]['worker'],
                                     TENDER_DATA[auction_type]['id'],
                                     TENDER_DATA[auction_type]['config'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('auction_type', type=str)
    parser.add_argument('action_type', type=str)

    args = parser.parse_args()
    main(args.auction_type, args.action_type, auctions_count=0)
