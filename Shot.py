# -*- coding: utf-8 -*-
"""
Shot.py
Created on Mon Nov 19 14:08:34 2012

@author: Shashwath
"""

from binary_reader import BinaryReader
import numpy as np
import xml.etree.ElementTree as ET
import os, sys
import struct
import filecmp
import pypyodbc

class ShotReader(object):
    """Reads a shot file and returns a dict for the header and an np.array for the data
    >>> filename = r"Shot_3255_.DAT"
    >>> shot = ShotReader(filename)
    >>> ascans = shot.ascans()
    >>> print ascans.shape
    (256, 2996)
    >>> print shot.header
    {'Origin': [0.0, 0.0, 0.0], 'Dimensions': [1533952, 1, 1], 'UddString': '<?CustomInfo CultureInfo=?><Section Name="Parameters"><Param Name="Version" Value="65537006" /><Param Name="DataFormat" Value="RF" /><Param Name="DataType" Value="UnsignedChar" /><Param Name="ConnectionID" Value="135" /></Section>', 'Spacing': [1.0, 1.0, 1.0], 'ScalarDataType': 'UnsignedChar', 'IsModified': True, 'NoOfComponents': '1', 'UnitZ': 'a.u.', 'UnitY': 'a.u.', 'UnitX': 'a.u.', 'AutoCreateMask': True, 'UddBinary': None}
    """
    def __init__(self, filename, num_channels=256):
        self.reader = BinaryReader(filename)
        length = self.reader.read('int32')
        header_data = self.reader.readstring(length)
        header_root = ET.fromstring(header_data, ET.XMLParser(encoding='utf-8'))
        self.data_size = self.reader.read('int32')
        self.number_of_channels = num_channels
        self.parse(header_root)


    def parse(self, root):
        _handlers = {'Origin': self.handle_point(float),
                     'Spacing':self.handle_point(float),
                     'Dimensions':self.handle_point(int),
                     'IsModified':self.handle_value(bool),
                     'AutoCreateMask':self.handle_value(bool)}
        self.header = {}
        for child in root:
            vals = None
            if child.tag in _handlers:
                vals = _handlers[child.tag](child)
            else:
                vals = self.handle_generic(child)
            if vals:
                self.header[vals[0]] = vals[1]

    def handle_generic(self, tag):
        return tag.tag, tag.text

    def handle_point(self, datatype):
        def inner(tag):
            value = [datatype(t.text) for t in tag]
            return tag.tag, value
        return inner

    def handle_value(self, datatype):
        def inner(tag):
            return tag.tag, datatype(tag.text)
        return inner

    def ascans(self):
        ascans = np.fromfile(self.reader.file, dtype=np.short, count=-1)
        shape = [self.number_of_channels, len(ascans)/self.number_of_channels]
        ascans.shape = shape
        return ascans

class ShotWriter(object):
    """Writes a shot file
    >>> filename = r"Shot_3255_.DAT"
    >>> shot = ShotReader(filename)
    >>> writer = ShotWriter('test.mdb')
    >>> header = shot.header
    >>> writer.write('Shot_3255_.DAT', shot.ascans(), shot.header['Origin'], shot.header['Spacing'], shot.header['Dimensions'], shot.header['UddString'], shot.header['ScalarDataType'],131072000)
    """
    def __init__(self, dbname, template='SingleChannelTemplate.mdb'):
        import os
        import shutil
        self.dbname = dbname

        shutil.copy(template, dbname)
        directory = os.path.splitext(dbname)[0]
        self.directory = directory
        try:
            os.makedirs(self.directory)
        except:
            pass
        self.connection = pypyodbc.win_connect_mdb(dbname)
        self.cursor = self.connection.cursor()

    def writeAxisInfo(self, scan, index):
        """Writes axis info into MDB
        >>> writer = ShotWriter('test.mdb')
        >>> writer.writeAxisInfo((10, 100, 1), (20, 100, 1))
        """
        updateQuery = 'UPDATE Axis SET StartPos=%d, EndPos=%d, StepValue=%d WHERE AxisId=%d'
        self.cursor.execute(updateQuery%(scan[0], scan[1], scan[2], 109))
        self.cursor.execute(updateQuery%(index[0], index[1], index[2], 110))
        self.cursor.commit()

    def write(self, filename, shot, origin, spacing, dimensions, udd, datatype, version):
        f = open(os.path.join(self.directory, filename), 'wb')
        headerData = self.createHeader(origin, spacing, dimensions, udd, datatype)
        header = ET.tostring(headerData, encoding='utf-8')
        headerLength = len(header)
        shotLength = len(shot.shape) == 1 and len(shot) or shot.shape[0] * shot.shape[1] * 2
        self.cursor.execute('''
        INSERT INTO DataSets (XValue, YValue, ZValue,
                              XScale, YScale, ZScale,
                              DataSize, StartPos, ConnectionId,
                              Version, UDDString, IsFileSystem,
                              FileName) VALUES (?,?,?,?,?,?,?,0,135,?,?,1,?)''', \
                              (origin[0], origin[1], origin[2], 1, 1, 1, \
                              shotLength, version, udd, filename))
        self.cursor.commit()
        f.write(struct.pack('i', headerLength))
        f.write(header)
        f.write(struct.pack('i', shotLength * 2))
        shot.tofile(f)

    def close(self):
        self.cursor.close()
        self.connection.close()
        pypyodbc.win_compact_mdb(self.dbname, self.dbname)

    def createHeader(self, origin, spacing, dimensions, udd, datatype):
        """Creates the header as an xml doc.
        >>> w = ShotWriter('test').createHeader([0,0,0], [1,1,1], [1,0,0], '<xml stuff />', 'UnsignedChar')
        >>> ET.dump(w)
        <LucidImage><ScalarDataType>UnsignedChar</ScalarDataType><Origin><double>0</double><double>0</double><double>0</double></Origin><UddString>&lt;xml stuff /&gt;</UddString><UddBinary /><IsModified>true</IsModified><Spacing><double>1</double><double>1</double><double>1</double></Spacing><Dimensions><int>1</int><int>0</int><int>0</int></Dimensions><AutoCreateMask>true</AutoCreateMask></LucidImage>
        """
        lucidImageTag = ET.Element('LucidImage')
        dtype = ET.SubElement(lucidImageTag, 'ScalarDataType')
        dtype.text = datatype
        originTag = ET.SubElement(lucidImageTag, 'Origin')
        ET.SubElement(originTag, 'double').text = str(origin[0])
        ET.SubElement(originTag, 'double').text = str(origin[1])
        ET.SubElement(originTag, 'double').text = str(origin[2])
        ET.SubElement(lucidImageTag, 'UddString').text = str(udd)
        ET.SubElement(lucidImageTag, 'UddBinary')
        ET.SubElement(lucidImageTag, 'IsModified').text = 'true'
        spacingTag = ET.SubElement(lucidImageTag, 'Spacing')
        ET.SubElement(spacingTag, 'double').text = str(spacing[0])
        ET.SubElement(spacingTag, 'double').text = str(spacing[1])
        ET.SubElement(spacingTag, 'double').text = str(spacing[2])
        dimsTag = ET.SubElement(lucidImageTag, 'Dimensions')
        ET.SubElement(dimsTag, 'int').text = str(dimensions[0])
        ET.SubElement(dimsTag, 'int').text = str(dimensions[1])
        ET.SubElement(dimsTag, 'int').text = str(dimensions[2])
        ET.SubElement(lucidImageTag, 'AutoCreateMask').text = 'true'
        return lucidImageTag

if __name__ =='__main__':
    import doctest
    doctest.testmod(verbose=True)
