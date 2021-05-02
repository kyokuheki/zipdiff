#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import zipfile
import logging
import collections
import itertools
import argparse
import pprint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(funcName)s(%(lineno)d): %(message)s")
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s:%(funcName)s(%(filename)s:%(lineno)d): %(message)s")
logger = logging.getLogger("zipdiff")
ZipCrc = collections.namedtuple('ZipCrc', ['crclist', 'crcdict', 'crcset', 'zf'])

def crclist_find(crclist: list, crc, size):
    return list(filter(lambda v: v[0:2] == (crc, size), crclist))

def zipcrc(zf: zipfile.ZipFile):
    crclist = [(zfi.CRC, zfi.file_size, zfi) for zfi in zf.infolist() if not zfi.is_dir()]
    crcdict = {(zfi.CRC, zfi.file_size): zfi for zfi in zf.infolist() if not zfi.is_dir()}
    crcset = set(crcdict.keys())
    if len(crclist) != len(crcset):
        crclist_find(crclist, )
        logger.warning('CRC,サイズ重複ファイルが存在する。{}: list={}, dict={}, set={}'.format(zf.filename, len(crclist), len(crcdict), len(crcset)))
    return ZipCrc(crclist, crcdict, crcset, zf)

def diff(zc1: ZipCrc, zc2: ZipCrc):
    result = {
        "zip1":{"filename":zc1.zf.filename},
        "zip2":{"filename":zc2.zf.filename},
    }
    symmetric_difference = zc1.crcset ^ zc2.crcset
    intersection = zc1.crcset & zc2.crcset
    def make_diff(symmetric_difference, zc: ZipCrc):
        r = []
        for i in symmetric_difference:
            for j in crclist_find(zc.crclist, *i):
                r.append({"crc":j[0], "size":j[1], "filename":j[2].orig_filename.encode('cp437').decode('cp932')})
        return r
    def make_intersection(intersection, zc1: ZipCrc, zc2: ZipCrc):
        r = []
        for i in intersection:
            entry = {"crc":i[0], "size":i[1], "zip1":[], "zip2":[]}
            for j in crclist_find(zc1.crclist, *i):
                entry["zip1"].append(j[2].orig_filename.encode('cp437').decode('cp932'))
            for j in crclist_find(zc2.crclist, *i):
                entry["zip2"].append(j[2].orig_filename.encode('cp437').decode('cp932'))
            r.append(entry)
        return r
    result["intersection_keys"] = intersection
    result["symmetric_difference_keys"] = symmetric_difference
    result["zip1"]["+"] = make_diff(symmetric_difference, zc1)
    result["zip2"]["+"] = make_diff(symmetric_difference, zc2)
    result["intersection"] = make_intersection(intersection, zc1, zc2)
    if len(symmetric_difference) < len(intersection):
        result["method"] = "symmetric_difference"
    else:
        result["method"] = "intersection"
    return result

def output(result):
    print("zip1: {}".format(result["zip1"]["filename"]))
    print("zip2: {}".format(result["zip2"]["filename"]))
    if result["method"] == "symmetric_difference":
        print('差分要素<共通要素。差分要素を表示対象とします。')
        if len(result["symmetric_difference_keys"]) == 0:
            print("格納ファイルに差分なし")
        else:
            pprint.pprint(result["zip1"])
            pprint.pprint(result["zip2"])
    else:
        print('共通要素<差分要素。共通要素を表示対象とします。')
        if len(result["intersection_keys"]) == 0:
            print("格納ファイルに一致なし")
        else:
            pprint.pprint(result["intersection"])
    return

def main():
    parser = argparse.ArgumentParser(
        description='zipdiff.py: Compare zip files by the CRC and file size of the files stored in them.')
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Make the operation more talkative")
    parser.add_argument(
        'zipfile',
        type=zipfile.ZipFile)
    parser.add_argument(
        'more',
        metavar='zipfile',
        nargs='+',
        type=zipfile.ZipFile)

    args = parser.parse_args()
    logger.setLevel(logging.INFO + 10*args.verbose)
    logger.info("args: {}".format(args))

    zfs = [args.zipfile] + args.more
    logger.info(pprint.pformat([zf.filename for zf in zfs]))
    zcs = [ (idx + 1, zipcrc(zf)) for idx, zf in enumerate(zfs)]

    for (idx1, zc1), (idx2, zc2) in itertools.combinations(zcs, 2):
        print("="*76)
        print(idx1, zc1.zf.filename)
        print(idx2, zc2.zf.filename)
        r = diff(zc1, zc2)
        logger.debug("-"*76)
        logger.debug("{}".format(pprint.pformat(r)))
        
        print()
        output(r)

if __name__ == "__main__":
    main()
