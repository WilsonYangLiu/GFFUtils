#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

import os, sys
import argparse
import GFFFile
import GTFFile
from argparse import RawTextHelpFormatter, FileType

def warning(msg):
	"""
	Print message to stderr
	"""
	sys.stderr.write("%s\n" % msg)

def main():
	parser = argparse.ArgumentParser(prog='enst2symbol', formatter_class=RawTextHelpFormatter, 
		description='''
   For id mapping: enst to symbol
''')
	parser.add_argument('-i', '--input', type=str, required=True,
		help='the gtf file')

	args = parser.parse_args()
	if not os.path.isfile(args.input):
		print('[ERROR]: {} dont exist'.format(args.input) )
		raise Exception

	for line in GTFFile.GTFIterator(args.input):
		attributes = line['attributes']
		if line.type == GFFFile.ANNOTATION:
			print('{}\t{}'.format(attributes['transcript_id'], attributes['gene_name'] ) )

if __name__ == "__main__":
    main()
