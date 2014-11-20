#!/bin/env python
#
#     GFFFile.py: classes for reading and manipulating data in GFF files
#     Copyright (C) University of Manchester 2012-4 Peter Briggs
#
########################################################################
#
# GFFFile.py
#
#########################################################################

import version
__version__ = version.__version__

"""GFFFile

Classes for reading data from GFF (Gene-Finding Format/General Feature
Format) files (see http://www.sanger.ac.uk/resources/software/gff/spec.html
for details of the format).

Classes
-------

There are a number of GFF-specific classes:

 * GFFIterator: line-by-line iteration through a GFF
 * GFFFile: read data from GFF into memory so it can be easily interrogated
 * GFFAttributes: read data from GFF attributes field to make it easier to
   handle
 * GFFID: handle data stored in 'ID' attribute

There is an additional base class:

 * OrderedDictionary: augumented dictionary which keeps its keys in the
   order they were added to the dictionary

Usage examples
--------------

Start by reading the data from a GFF file into a GFFFile object:

>>> gff = GFFFile('my.gff')

To iterate over all lines in the GFFFile object and print the
feature type:

>>> for line in gff:
>>>    print line['feature']

(To iterate over all lines in the GFF without caching in memory,
printing feature types for annotation records:

>>> for line in GFFIterator('my.gff'):
>>>    if line.type == ANNOTATION:
>>>       print line['feature']

)

The 'attributes' data of each annotation record are automatically converted
to a GFFAttributes object, which allows the values of named attributes to be
referenced directly. For example, if the attributes string is:

"ID=1690892742066571889;SGD=YEL026W;Gene=Sbay_5.43;Parent=Sbay_5.43"

then the value of the 'Parent' attribute can be obtained using

>>> print line['attributes']['Parent']

To iterate over all lines and extract 'ID' field from attributes:

>>> for line in gff:
>>>    if 'ID' in line['attributes']['ID']:
>>>       print line['attributes']['ID']

To iterate over all lines and print just the 'name' part of the
'ID' attribute:

>>> for line in gff:
>>>    if 'ID' in line['attributes']
>>>       print GFFID(line['attributes']['ID']).name

"""

#######################################################################
# Import modules that this module depends on
#######################################################################

try:
    from TabFile import TabFile,TabDataLine
except ImportError:
    from bcftbx.TabFile import TabFile,TabDataLine
import logging
import copy
import urllib
from collections import Iterator

#######################################################################
# Constants/globals
#######################################################################

# Columns in GFF/GTF files
GFF_COLUMNS = ('seqname',
               'source',
               'feature',
               'start',
               'end',
               'score',
               'strand',
               'frame',
               'attributes')

# Types of line in GFF files
#
# "Pragma" line starts with '##'
PRAGMA = 0
# "Comment" line starts with single '#'
COMMENT = 1
# "Annotation" lines are tab-delimited fields containing annotation data 
ANNOTATION = 2

#######################################################################
# Class definitions
#######################################################################

class GFFDataLine(TabDataLine):
    """Data line specific to GFF files

    Subclass of TabDataLine which automatically converts data in the
    attributes column into a GFFAttributes object. This allows GFF
    attributes to be accessed directly using the syntax
    gff_line['attributes']['Parent'].
    """
    def __init__(self,line=None,column_names=GFF_COLUMNS,lineno=None,delimiter='\t',
                 gff_line_type=None):
        TabDataLine.__init__(self,line=line,column_names=column_names,
                             lineno=lineno,delimiter=delimiter)
        # Convert attributes to GFFAttributes object
        self['attributes'] = GFFAttributes(self['attributes'])
        # Metadata
        self.__type = gff_line_type

    @property
    def type(self):
        """'Type' (pragma, comment, annotation)  associated with the GFF data line

        'type' is either None, or one of the module-level constants PRAGMA, COMMENT,
        ANNOTATION, indicating the type of data held by the line.
        """
        return self.__type

class GFFFile(TabFile):
    """Class for handling GFF files in-memory

    Subclass of TabFile which uses the GFFIterator to process the
    contents of a GFF file and store annotation lines as GFFDataLines.

    Data from the file can then be extracted and modified using the
    methods of the TabFile and GFFDataLine classes.

    See http://www.sanger.ac.uk/resources/software/gff/spec.html
    for the GFF specification.
    """
    def __init__(self,gff_file,fp=None,gffdataline=GFFDataLine,format='gff'):
        # Storage for format info
        self._format = format
        self._version = None
        # Initialise empty TabFile
        TabFile.__init__(self,None,fp=None,
                         tab_data_line=GFFDataLine,
                         column_names=GFF_COLUMNS)
        # Populate by iterating over GFF file
        for line in GFFIterator(gff_file=gff_file,fp=fp,
                                gffdataline=gffdataline):
           if line.type == ANNOTATION:
                # Append to TabFile
                self.append(tabdataline=line)
           elif line.type == PRAGMA:
               # Try to extract relevant data
               pragma = str(line)[2:].split()
               if pragma[0] == 'gff-version':
                   self._version = pragma[1]

    def write(self,filen):
        """Write the GFF data to an output GFF

        Arguments:
          filen: name of file to write to
        """
        fp = open(filen,'w')
        if self.format == 'gff':
            fp.write("##gff-version 3\n")
        TabFile.write(self,fp=fp)
        fp.close()

    @property
    def format(self):
        """Return the format e.g. 'gff'

        """
        return self._format

    @property
    def version(self):
        """Return the version e.g. '3'

        """
        return self._version

class OrderedDictionary:
    """Augumented dictionary which keeps keys in order

    OrderedDictionary provides an augmented Python dictionary
    class which keeps the dictionary keys in the order they are
    added to the object.

    Items are added, modified and removed as with a standard
    dictionary e.g.:

    >>> d[key] = value
    >>> value = d[key]
    >>> del(d[key])

    The 'keys()' method returns the OrderedDictionary's keys in
    the correct order.
    """
    def __init__(self):
        self.__keys = []
        self.__dict = {}

    def __getitem__(self,key):
        if key not in self.__keys:
            raise KeyError
        return self.__dict[key]

    def __setitem__(self,key,value):
        if key not in self.__keys:
            self.__keys.append(key)
        self.__dict[key] = value

    def __delitem__(self,key):
        try:
            i = self.__keys.index(key)
            del(self.__keys[i])
            del(self.__dict[key])
        except ValueError:
            raise KeyError

    def __len__(self):
        return len(self.__keys)

    def __contains__(self,key):
        return key in self.__keys

    def __iter__(self):
        return iter(self.__keys)

    def keys(self):
        return copy.copy(self.__keys)

    def insert(self,i,key,value):
        if key not in self.__keys:
            self.__keys.insert(i,key)
            self.__dict[key] = value
        else:
            raise KeyError, "Key '%s' already exists" % key

class GFFAttributes(OrderedDictionary):
    """Class for handling GFF 'attribute' data

    The GFF 'attribute' data consists of semi-colon separated
    data items, which might be single values or 'key=value'
    pairs.

    Given an input string of this form, a GFFAttributes
    object provides access to the keys via the keys() method
    (lists all keys in the order they were encountered), and
    access to values via the GFFAttributes[key] syntax.

    Keyed data can be modified and deleted via this syntax.

    The values without keys can be accessed as a list via the
    nokeys() method. Special characters that have been escaped
    using "percent encoding" (e.g. semicolons, equals, tabs etc)
    are automatically converted back to their original values
    (e.g. ';' rather than '%3B').

    str(GFFAttributes) returns the attribute data as a
    string representation which restores the original format
    found in the GFF file (i.e. semi-column separated data
    items with single values or 'key=value' pairs as
    appropriate). Values which contain special characters
    will be escaped appropriately using URL percent encoding
    (i.e. the reverse of the decoding process).
    """
    def __init__(self,attribute_data=None):
        OrderedDictionary.__init__(self)
        self.__nokeys = []
        # Special attributes which can have multiple values
        self.__multivalued_attributes = ('Parent',
                                         'Alias',
                                         'Note',
                                         'Dbxref',
                                         'Ontology_term')
        # Flag indicating whether to encode values on output
        self.__encode_values = True
        # Flag indicating whether data came with trailing semicolon
        self.__trailing_semicolon = False
        # Extract individual data items
        if attribute_data:
            for item in attribute_data.split(';'):
                if not item:
                    continue
                try:
                    i = item.index('=')
                    key = item[:i].strip()
                    value = item[i+1:].strip()
                except ValueError:
                    # No equals sign
                    key = ''
                    value = item.strip()
                # Percent-decode value
                value = urllib.unquote(value)
                # Store data
                if key == '':
                    # No key: store in a list
                    self.__nokeys.append(value)
                else:
                    # Store key-value pair
                    self[key] = value
            self.__trailing_semicolon = attribute_data.endswith(';')

    def nokeys(self):
        return self.__nokeys

    def encode(self,new_setting=None):
        """Query or set the value of the 'encoding' flag

        By default attribute values are encoded when written as a
        string i.e. special characters are escaped using HTML-style
        encoding to convert them to "percent codes" e.g. '%3B'.
        This method allows this encoding to be turned on or off
        explicitly.

        To query the current setting, invoke the method without
        arguments e.g.:

        >>> attr.encode()
        ... True

        To turn encoding on or off, invoke with a boolean argument,
        e.g.:

        >>> attr.encode(False)  # Turns encoding off
        ... False

        Note that turning the decoding off is not recommended when
        writing the attributes back to a GFF file.
        
        Arguments:
          new_setting: (optional) the new value for the encoding
            flag - True to turn encoding on, False to turn it off

        Returns:
          Value of the encoding flag, indicating whether encoding
          is on (True) or off (False).
        """
        if new_setting in (True,False):
            self.__encode_values = new_setting
        elif new_setting is not None:
            raise ValueError, "bad value '%s': can only be True or False" % new_setting
        return self.__encode_values

    def __escape_value(self,key,value):
        """Internal: return escaped value of input string

        Performs the URL percent encoding of values for the GFF
        attributes.

        Note that for certain predefined keys, an unescaped comma
        is allowed in the value. For all others commas will be
        escaped.

        Arguments:
          key: name of the attribute that the value belongs to
          value: the string to be encoded
        """
        if key in self.__multivalued_attributes:
            return urllib.quote(value,safe=" ,:^*$@!+?|")
        else:
            return urllib.quote(self[key],safe=" :^*$@!+?|")

    def __repr__(self):
        items = []
        if self.__encode_values:
            # Percent encode the attributes
            for key in self.keys():
                items.append("%s=%s" % (key,self.__escape_value(key,self[key])))
        else:
            # Don't encode the attributes
            for key in self.keys():
                items.append("%s=%s" % (key,self[key]))
        # Add nokeys items
        for item in self.__nokeys:
            items.append(item)
        # Dealing with trailing semicolon
        if self.__trailing_semicolon:
            items.append('')
        return ';'.join(items)

class GFFID:
    """Class for handling ID attribute in GFF data

    The GFFID class takes an ID string which is expected to be of
    one of the forms

    <name> (e.g. 'XYZ123-A')

    or
    
    <code>:<name>:<index> (e.g. 'CDS:XYZ123-A:2')

    The components can be queried and changed via the code,
    name and index properties of the class, e.g.

    >>> code = GFFID('CDS:XYZ123-A:2').code

    etc

    If there is no code then this is returned as an empty string;
    if there is no index then this is returned as 0.

    Doing e.g. str(gffid) returns the appropriate string
    representation.
    """
    def __init__(self,gff_id):
        items = str(gff_id).split(':')
        if len(items) == 1:
            self.code = ''
            self.name = gff_id
        else:
            self.code = items[0]
            self.name = items[1]
        if len(items) > 2:
            try:
                self.index = int(items[2])
            except ValueError:
                print "Bad id? %s %s" % (gff_id,items)
                raise ValueError
        else:
            self.index = 0
            
    def __repr__(self):
        if not self.code:
            return "%s" % self.name
        else:
            return "%s:%s:%d" % (self.code,self.name,self.index)

class GFFIterator(Iterator):
    """GFFIterator

    Class to loop over all records in a GFF file, returning a GFFDataLine
    object for each record.

    Example looping over all reads
    >>> for record in GFFIterator(gff_file):
    >>>    print record
    """

    def __init__(self,gff_file=None,fp=None,gffdataline=GFFDataLine):
        """Create a new GFFIterator

        Arguments:
           gff_file: name of the GFF file to iterate through
           fp: file-like object to read GFF data from
           gffdataline: GFFDataLine-like class to instantiate
             and return for each record in the GFF
        """
        if fp is not None:
            self.__fp = fp
            self.__close_fp = False
        else:
            self.__fp = open(gff_file,'rU')
            self.__close_fp = True
        self.__gffdataline = gffdataline
        self.__lineno = 0

    def next(self):
        """Return next record from GFF file as a GFFDataLine object
        """
        line = self.__fp.readline()
        self.__lineno += 1
        if line != '':
            # Set type for line
            if line.startswith("##"):
                # Pragma
                type_ = PRAGMA
            elif line.startswith("#"):
                # Comment line
                type_ = COMMENT
            else:
                # Annotation line
                type_ = ANNOTATION
            # Convert to GFFDataLine
            return self.__gffdataline(line=line,lineno=self.__lineno,gff_line_type=type_)
        else:
            # Reached EOF
            if self.__close_fp: self.__fp.close()
            raise StopIteration

#######################################################################
# Tests
#######################################################################

import unittest
import cStringIO

class TestGFFIterator(unittest.TestCase):
    """Basic tests for iterating through a GFF file
    """

    def setUp(self):
        # Example GFF file fragment
        self.fp = cStringIO.StringIO(
"""##gff-version 3
# generated: Wed Feb 21 12:01:58 2012
DDB0123458	Sequencing Center	chromosome	1	4923596	.	+	.	ID=DDB0232428;Name=1
DDB0232428	Sequencing Center	contig	101	174493	.	+	.	ID=DDB0232440;Parent=DDB0232428;Name=DDB0232440;description=Contig generated from contig finding genome version 2.5;Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02
DDB0232428	.	gene	1890	3287	.	+	.	ID=DDB_G0267178;Name=DDB_G0267178_RTE;description=ORF2 protein fragment of DIRS1 retrotransposon%3B refer to Genbank M11339 for full-length element
DDB0232428	Sequencing Center	mRNA	1890	3287	.	+	.	ID=DDB0216437;Parent=DDB_G0267178;Name=DDB0216437;description=JC1V2_0_00003: Obtained from the Dictyostelium Genome Consortium at The Wellcome Trust Sanger Institute;translation_start=1;Dbxref=Protein Accession Version:EAL73826.1,Inparanoid V. 5.1:DDB0216437,Protein Accession Number:EAL73826.1,Protein GI Number:60475899,UniProt:Q55H43,Genome V. 2.0 ID:JC1V2_0_00003
DDB0232428	Sequencing Center	exon	1890	3287	.	+	.	Parent=DDB0216437
DDB0232428	Sequencing Center	CDS	1890	3287	.	+	.	Parent=DDB0216437
""")

    def test_gff_iterator(self):
        """Test iteration over a file-like object
        """
        # Count number of lines, and number of each type
        nlines = 0
        npragma = 0
        ncomment = 0
        nannotation = 0
        # Iterate through GFF file fragment
        for line in GFFIterator(fp=self.fp):
            nlines += 1
            self.assertNotEqual(line.type,None)
            self.assertEqual(line.lineno(),nlines)
            if line.type == PRAGMA: npragma += 1
            if line.type == COMMENT: ncomment += 1
            if line.type == ANNOTATION: nannotation += 1
        # Check counts
        self.assertEqual(nlines,8)
        self.assertEqual(npragma,1)
        self.assertEqual(ncomment,1)
        self.assertEqual(nannotation,6)

class TestGFFFile(unittest.TestCase):
    """Basic unit tests for the GFFFile class
    """

    def setUp(self):
        # Example GFF file fragment
        self.fp = cStringIO.StringIO(
"""##gff-version 3
# generated: Wed Feb 21 12:01:58 2012
DDB0123458	Sequencing Center	chromosome	1	4923596	.	+	.	ID=DDB0232428;Name=1
DDB0232428	Sequencing Center	contig	101	174493	.	+	.	ID=DDB0232440;Parent=DDB0232428;Name=DDB0232440;description=Contig generated from contig finding genome version 2.5;Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02
DDB0232428	.	gene	1890	3287	.	+	.	ID=DDB_G0267178;Name=DDB_G0267178_RTE;description=ORF2 protein fragment of DIRS1 retrotransposon%3B refer to Genbank M11339 for full-length element
DDB0232428	Sequencing Center	mRNA	1890	3287	.	+	.	ID=DDB0216437;Parent=DDB_G0267178;Name=DDB0216437;description=JC1V2_0_00003: Obtained from the Dictyostelium Genome Consortium at The Wellcome Trust Sanger Institute;translation_start=1;Dbxref=Protein Accession Version:EAL73826.1,Inparanoid V. 5.1:DDB0216437,Protein Accession Number:EAL73826.1,Protein GI Number:60475899,UniProt:Q55H43,Genome V. 2.0 ID:JC1V2_0_00003
DDB0232428	Sequencing Center	exon	1890	3287	.	+	.	Parent=DDB0216437
DDB0232428	Sequencing Center	CDS	1890	3287	.	+	.	Parent=DDB0216437
""")

    def test_read_in_gff(self):
        """Test that the GFF data can be read in
        """
        gff = GFFFile("test.gff",self.fp)
        # Check format and version
        self.assertEqual(gff.format,'gff')
        self.assertEqual(gff.version,'3')
        # There should be 6 lines of data
        self.assertEqual(len(gff),6)
        # Check the feature names are correct
        feature = ('chromosome','contig','gene','mRNA','exon','CDS')
        for i in range(len(gff)):
            self.assertEqual(feature[i],gff[i]['feature'],
                             "Incorrect feature '%s' on data line %d" % (gff[i]['feature'],i))

class TestGFFAttributes(unittest.TestCase):
    """Unit tests for GFFAttributes class
    """

    def test_extract_attributes(self):
        """Test that attribute data can be extracted
        """
        attributes = "ID=DDB0232440;Parent=DDB0232428;Name=DDB0232440;description=Contig generated from contig finding genome version 2.5;Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02"
        attr = GFFAttributes(attributes)
        self.assertTrue('ID' in attr)
        self.assertEqual(attr['ID'],'DDB0232440')
        self.assertTrue('Parent' in attr)
        self.assertEqual(attr['Parent'],'DDB0232428')
        self.assertTrue('Name' in attr)
        self.assertEqual(attr['Name'],'DDB0232440')
        self.assertTrue('description' in attr)
        self.assertEqual(attr['description'],'Contig generated from contig finding genome version 2.5')
        self.assertTrue('Dbxref' in attr)
        self.assertEqual(attr['Dbxref'],'Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02')
        self.assertFalse('not_here' in attr)

    def test_percent_decoding(self):
        """Test that percent decoding works on attribute lists
        """
        attributes = "ID=DDB_G0789012;Name=DDB_G0789012_ps;description=putative pseudogene%3B similar to a family of genes%2C including %3Ca href%3D%22%2Fgene%2FDDB_G0234567%22%3EDDB_G0234567%3C%2Fa%3E"
        attr = GFFAttributes(attributes)
        self.assertEqual(attr['ID'],'DDB_G0789012')
        self.assertEqual(attr['Name'],'DDB_G0789012_ps')
        self.assertEqual(attr['description'],'putative pseudogene; similar to a family of genes, including <a href="/gene/DDB_G0234567">DDB_G0234567</a>')

    def test_percent_encoding(self):
        """Test that attributes are properly re-encoded
        """
        dbxref = "Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02"
        self.assertEqual(dbxref,str(GFFAttributes(dbxref)))
        parent = "Parent=AF2312,AB2812,abc-3"
        self.assertEqual(parent,str(GFFAttributes(parent)))
        description = "description=putative pseudogene%3B similar to a family of genes%2C including %3Ca href%3D%22%2Fgene%2FDDB_G0234567%22%3EDDB_G0234567%3C%2Fa%3E"
        self.assertEqual(description,str(GFFAttributes(description)))

    def test_recover_representation(self):
        """Test that __repr__ returns original string
        """
        attributes = "ID=DDB0232440;Parent=DDB0232428;Name=DDB0232440;description=Contig generated from contig finding genome version 2.5;Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02"
        attr = GFFAttributes(attributes)
        self.assertEqual(attributes,str(attr))

    def test_recover_representation_with_percent_encoding(self):
        """Test that __repr__ returns original string with percent encoding
        """
        attributes = "ID=DDB_G0789012;Name=DDB_G0789012_ps;description=putative pseudogene%3B similar to a family of genes%2C including %3Ca href%3D%22%2Fgene%2FDDB_G0234567%22%3EDDB_G0234567%3C%2Fa%3E"
        attr = GFFAttributes(attributes)
        self.assertEqual(attributes,str(attr))

    def test_recover_representation_with_trailing_semicolon(self):
        """Test that __repr__ returns original string with trailing semicolon
        """
        attributes = "ID=DDB0232440;Parent=DDB0232428;Name=DDB0232440;description=Contig generated from contig finding genome version 2.5;Dbxref=Contig GI Number:90970918,Accession Number:AAFI02000001,SeqID for Genbank:DDB0232440.02;"
        attr = GFFAttributes(attributes)
        self.assertEqual(attributes,str(attr))

    def test_switch_off_encoding(self):
        """Test that __repr__ returns unescaped strings when encoding is off
        """      
        attributes = "ID=DDB_G0789012;Name=DDB_G0789012_ps;description=putative pseudogene%3B similar to a family of genes%2C including %3Ca href%3D%22%2Fgene%2FDDB_G0234567%22%3EDDB_G0234567%3C%2Fa%3E"
        
        attr = GFFAttributes(attributes)
        self.assertTrue(attr.encode())
        self.assertEqual(attributes,str(attr))
        self.assertTrue(attr.encode(True))
        self.assertEqual(attributes,str(attr))
        self.assertFalse(attr.encode(False))
        self.assertEqual("ID=DDB_G0789012;Name=DDB_G0789012_ps;description=putative pseudogene; similar to a family of genes, including <a href=\"/gene/DDB_G0234567\">DDB_G0234567</a>",str(attr))

    def test_empty_attributes_string(self):
        """Test that empty input generates empty output
        """
        attr = GFFAttributes('')
        self.assertEqual('',str(attr))
        attr['ID'] = 'test'
        self.assertEqual('ID=test',str(attr))

    def test_no_null_attributes_for_trailing_semicolon(self):
        """Test trailing ';' in attributes doesn't result in empty 'no-key' attribute
        """
        attr = GFFAttributes("ID=GOAT_ENSP00000332624;")
        self.assertEqual(attr.keys(),['ID'])
        self.assertEqual(attr['ID'],"GOAT_ENSP00000332624")
        self.assertEqual(attr.nokeys(),[])

    def test_nokeys_attributes(self):
        """Test that 'nokeys' attributes are read
        """
        attributes = "ID=GOAT_ENSP00000332668;Shift=2;589008-589009;589535-589539"
        attr = GFFAttributes(attributes)
        self.assertEqual(attr.keys(),['ID','Shift'])
        self.assertEqual(attr['ID'],"GOAT_ENSP00000332668")
        self.assertEqual(attr['Shift'],"2")
        self.assertEqual(attr.nokeys(),['589008-589009','589535-589539'])
        self.assertEqual(str(attr),attributes)

    def test_manipulate_nokeys_attributes(self):
        """Test that 'nokeys' attributes can be manipulated
        """
        attr = GFFAttributes("ID=GOAT_ENSP00000332668;Shift=2;589008-589009;589535-589539")
        self.assertEqual(attr.nokeys(),['589008-589009','589535-589539'])
        nokeys = attr.nokeys()
        nokeys.append('Test')
        self.assertEqual(attr.nokeys(),['589008-589009','589535-589539','Test'])
        del(nokeys[:])
        self.assertEqual(attr.nokeys(),[])

class TestGFFID(unittest.TestCase):
    """Unit tests for GFFID class
    """

    def test_simple_ID(self):
        """Check that name and index can be extracted from ID without code or index
        """
        gffid = GFFID('XYZ123-A')
        self.assertEqual(gffid.code,'')
        self.assertEqual(gffid.name,'XYZ123-A')
        self.assertEqual(gffid.index,0)
        self.assertEqual(str(gffid),'XYZ123-A')        

    def test_full_ID(self):
        """Check that code, name and index can be extracted from full ID
        """
        gffid = GFFID('CDS:XYZ123-A:2')
        self.assertEqual(gffid.code,'CDS')
        self.assertEqual(gffid.name,'XYZ123-A')
        self.assertEqual(gffid.index,2)
        self.assertEqual(str(gffid),'CDS:XYZ123-A:2')

class TestOrderedDictionary(unittest.TestCase):
    """Unit tests for the OrderedDictionary class
    """

    def test_get_and_set(self):
        """Add and retrieve data
        """
        d = OrderedDictionary()
        self.assertEqual(len(d),0)
        d['hello'] = 'goodbye'
        self.assertEqual(d['hello'],'goodbye')

    def test_insert(self):
        """Insert items
        """
        d = OrderedDictionary()
        d['hello'] = 'goodbye'
        self.assertEqual(d.keys(),['hello'])
        self.assertEqual(len(d),1)
        # Insert at start of list
        d.insert(0,'stanley','fetcher')
        self.assertEqual(d.keys(),['stanley','hello'])
        self.assertEqual(len(d),2)
        self.assertEqual(d['stanley'],'fetcher')
        self.assertEqual(d['hello'],'goodbye')
        # Insert in middle
        d.insert(1,'monty','python')
        self.assertEqual(d.keys(),['stanley','monty','hello'])
        self.assertEqual(len(d),3)
        self.assertEqual(d['stanley'],'fetcher')
        self.assertEqual(d['monty'],'python')
        self.assertEqual(d['hello'],'goodbye')

    def test_keeps_things_in_order(self):
        """Check that items are returned in same order as added
        """
        d = OrderedDictionary()
        d['hello'] = 'goodbye'
        d['stanley'] = 'fletcher'
        d['monty'] = 'python'
        self.assertEqual(d.keys(),['hello','stanley','monty'])

    def test_iteration_over_keys(self):
        """Check iterating over keys
        """
        d = OrderedDictionary()
        d['hello'] = 'goodbye'
        d['stanley'] = 'fletcher'
        d['monty'] = 'python'
        try:
            for i in d:
                pass
        except KeyError:
            self.fail("Iteration over OrderedDictionary failed")

#######################################################################
# Main program
#######################################################################

if __name__ == "__main__":
    # Turn off most logging output for tests
    logging.getLogger().setLevel(logging.CRITICAL)
    # Run tests
    unittest.main()
