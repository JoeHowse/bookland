# #!/usr/bin/env python
#
#   productcode.py - classes for Product Codes and bar code symbols
#
#   Focused on ISBN and ISMN bar codes but generally applicable to
#   all EAN-13's.
#
#   Copyright (C) 2007 Judah Milgram     
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   Because this program copies a portion of itself into its output
#   file, its output files are also copyright the author and licensed
#   under the GPL.  Relevant provisions of the GPL notwithstanding,
#   the author licenses users to use and redistribute output files
#   generated by this program without restriction.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#     
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
#   ===============================================================
#
# Product Code Hierarchy:
#
# ProductCode
#     |
#     ------------------
#     |       |        |
#    [UPC]  ISBN10   ISMN
#     |
#     ---------
#     |       |
#    [UPCA]    UPC5
#     |
#    EAN13
#     |
#    ISBN13

from types import *
import re
import string

A="A";B="B";C="C";O="O";E="E"
UPCABITS = [{O:"0001101",E:"1110010"},
            {O:"0011001",E:"1100110"},
            {O:"0010011",E:"1101100"},
            {O:"0111101",E:"1000010"},
            {O:"0100011",E:"1011100"},
            {O:"0110001",E:"1001110"},
            {O:"0101111",E:"1010000"},
            {O:"0111011",E:"1000100"},
            {O:"0110111",E:"1001000"},
            {O:"0001011",E:"1110100"}]


UPCAPARITY = [ "OOOOOOEEEEEE" ] * 10
UPCEBITS = [{O:"0001101",E:"0100111"},
            {O:"0011001",E:"0110011"},
            {O:"0010011",E:"0011011"},
            {O:"0111101",E:"0100001"},
            {O:"0100011",E:"0011101"},
            {O:"0110001",E:"0111001"},
            {O:"0101111",E:"0000101"},
            {O:"0111011",E:"0010001"},
            {O:"0110111",E:"0001001"},
            {O:"0001011",E:"0010111"}]
# what about UPCEPARITY? Don't need for isbn.
UPC5BITS = UPCEBITS
UPC5PARITY = ["EEOOO","EOEOO","EOOEO","EOOOE","OEEOO",
              "OOEEO","OOOEE","OEOEO","OEOOE","OOEOE"]
EAN13BITS = [{A:"0001101", B:"0100111", C:"1110010"},
             {A:"0011001", B:"0110011", C:"1100110"},
             {A:"0010011", B:"0011011", C:"1101100"},
             {A:"0111101", B:"0100001", C:"1000010"},
             {A:"0100011", B:"0011101", C:"1011100"},
             {A:"0110001", B:"0111001", C:"1001110"},
             {A:"0101111", B:"0000101", C:"1010000"},
             {A:"0111011", B:"0010001", C:"1000100"},
             {A:"0110111", B:"0001001", C:"1001000"},
             {A:"0001011", B:"0010111", C:"1110100"}]
EAN13PARITY = list(map(lambda x: x+"CCCCCC",
                  ["AAAAAA","AABABB","AABBAB","AABBBA","ABAABB",
                   "ABBAAB","ABBBAA","ABABAB","ABABBA","ABBABA"]))

class ProductCodeError(Exception):
    msgs=[]
    def __init__(self,msg=None):
        if msg:
            self.msgs.append(msg)
    def __str__(self):
        return "\n".join(self.msgs)

def makeCharMap(*dicts):
    # Make a character map for parsing a produce code string.
    rval = {}
    # assume 0-9 always present:
    for i in range(10):
        key = "%s" % i
        rval[key] = i
    for dict in dicts:
        for key in dict.keys():
            rval[key] = dict[key] 
    return rval

def parse(s,firstCharMap,lastCharMap,otherCharMap):
    # Extract the underlying digits from a product code string
    # Parse errors get raised as KeyError.
    digits = []
    d = firstCharMap[s[0]]
    if type(d)==int or d==None: digits.append(d)
    for c in s[1:-1]:
        d = otherCharMap[c]
        if type(d)==int or d==None: digits.append(d)
    d = lastCharMap[s[-1]]
    if type(d)==int or d==None: digits.append(d)
    return digits

class ProductCode:
    # Base class for all product codes.
    # label is the string used in __repr__
    # type is the product code type - could differ from label
    type = "ProductCode"
    label = ""
    def __init__(self,s):
        self.givenString = s
        self.s = s.upper()
        try:
            self.digits = parse(s,self.firstCharMap,
                                  self.lastCharMap,
                                  self.otherCharMap)
        except KeyError as m:
            msg = "%s: %s invalid here" % (self.type,m)
            raise ProductCodeError(msg)
        i = self.resolveChecksum()
        if i != None:
            # Replace wild card with its value
            # This depends on having only one wildcard "*"
            c = self.int2char(i)
            self.s = re.sub("\*",c,self.s)
        self.realityCheck()
        self.checkDigit = self.digits[-1]
    def int2char(self,n):
        # Ripe for override, e.g. to map "X" to 10 in ISBN
        rval = "%s" % n
        if len(rval) > 1:
            msg = "%s: Internal error" % self.type
            raise ProductCodeError(msg)
        return rval

    def remainder(self):
        # The weighted sum, modulo self.magic
        if len(self.digits) != len(self.weights):
            msg = "%s: wrong number of digits" % self.type
            raise ProductCodeError(msg)
        sum = 0
        for p in range(len(self.digits)):
            sum += self.digits[p]*self.weights[p]
        return sum % self.magic

    def resolveChecksum(self):
        # resolve checksum
        nWild = self.digits.count(None)
        if nWild == 0:
            # No wildcards
            if self.remainder()==0:
                return None
            else:
                msg = "%s: checksum error" % self.type
                raise ProductCodeError(msg)
        elif nWild == 1:
            # Solve for wildcard value
            iWild=self.digits.index(None)
            for i in range(10):
                self.digits[iWild]=i
                if self.remainder()==0:
                    return i
        else:
            msg = "%s: too many wildcard digits." % self.type
            raise ProductCodeError(msg)
    def realityCheck(self):
        # Probably superfluous ... errors would have been caught already
        msgs = []
        if len(self.weights) < len(self.digits):
            msgs.append("%s: Too many digits" % self.type)
        elif len(self.weights) > len(self.digits):
            msgs.append("%s: Not enough digits" % self.type)
        if not self.s[0] in self.firstCharMap.keys():
            msgs.append("%s: Illegal first character" % self.type)
        if not self.s[-1] in self.lastCharMap.keys():
            msgs.append("%s: Illegal final character" % self.type)
        for c in self.s[1:-1]:
            if not c in self.otherCharMap.keys():
                msgs.append("%s: Illegal character" % self.type)
        if re.search("--|  ",self.s):
            msgs.append("%s: Repeated seperator" % self.type)
        if msgs:
            msg = "\n".join(msgs)
            raise ProductCodeError(msg)
    def __repr__(self):
        rval = self.s
        if self.label:
            rval = "%s %s" % (self.label,rval)
        return rval
    
class UPC(ProductCode):
    # Includes UPC-A, UPC-E, EAN-13 (sorry), UPC-5 et al.
    firstCharMap = makeCharMap({"*":None})
    lastCharMap = makeCharMap({"*":None})
    otherCharMap = makeCharMap({"*":None,"-":"-"})
    def __init__(self,s):
        ProductCode.__init__(self,s)

    def setbits(self,digits):
        # UPC (all)
        self.bits=""
        for p in range(len(digits)):
            digit = digits[p]
            parity=self.parityPattern[p]
            bit=self.bitchar[digit][parity]
            self.bits=self.bits + bit
class UPCA(UPC):
    type="UPCA"
    label=""
    def __init__(self,s):
#        self.weights=6*[3,1]
#        self.magic=10
        UPC.__init__(self,s)
#        self.parityPattern = UPCAPARITY[self.checkDigit]
#        self.bitchar = UPCABITS
#        self.setbits()
    def setbits(self):
        return UPC.setbits(self,self.digits[1:])
class EAN13(UPCA):
    type="EAN13"
    label="EAN13"
    def __init__(self,s):
        self.weights=[1] + 6*[3,1] 
        self.magic=10
        UPCA.__init__(self,s)
        # N.B. parity pattern based on leftmost digit, the UCC Spec calls this
        # the "13th" digit. It's not the check digit!
        self.parityPattern = EAN13PARITY[self.digits[0]]
        self.bitchar = EAN13BITS
        self.setbits()
        leftBits = self.bits[0:42]
        rightBits = self.bits[42:]
        leftGuard="L0L"
        rightGuard="L0L"
        center="0L0L0"
        self.bits = leftGuard + leftBits + center + rightBits + rightGuard
        self.leftDigits = "".join(map(str,self.digits[1:7]))
        self.rightDigits = "".join(map(str,self.digits[7:13]))
    def as13(self):
        return self
class UPC5(UPC):
    # UPC2/5 checksum not actually in the number, but we need it.
    # So we treat it internally as a 6-digit number!
    # Also note funky definition of check digit
    def __init__(self,s):
        self.weights= [3,9,3,9,3,-1]
        self.magic = 10
        self.firstCharMap = makeCharMap()
        self.otherCharMap = makeCharMap()
        self.lastCharMap = makeCharMap({"*":None})
        self.type = "UPC5"
        self.label = ""
        s = s+"*"
        UPC.__init__(self,s)
        # Now cut off the check digit:
        # Kludgy.
        self.s = self.s[:5]
        self.parityPattern = UPC5PARITY[self.checkDigit]
        self.bitchar = UPC5BITS
        self.setbits(self.digits[:5])
        leftGuard="1011"
        # no right guard for UPC 5-digit add-on
        # Have to insert pesky delineators:
        delineator = "01"
        self.bits = leftGuard + \
                    self.bits[0:7] + delineator + \
                    self.bits[7:14] + delineator + \
                    self.bits[14:21] + delineator + \
                    self.bits[21:28] + delineator + \
                    self.bits[28:35]

class ISBN13(EAN13):
    def __init__(self,s):
        self.type = "ISBN13"
        self.label = "ISBN"
        EAN13.__init__(self,s)
        if not s[0] in "9*" or \
           not s[1] in "7*" or \
           not s[2] in "89*":
            msg = "%s: must begin with 978 or 979" % self.type
            raise ProductCodeError(msg)
    def as13(self):
        return self
class ISBN10(ProductCode):
    def __init__(self,s):
        self.type = "ISBN10"
        self.label = "ISBN"
        self.firstCharMap = makeCharMap({"*":None})
        self.lastCharMap = makeCharMap({"*":None,"X":10,"x":10})
        self.otherCharMap = makeCharMap({"*":None,"-":"-"})
        self.weights=range(10,0,-1)
        self.magic=11
        ProductCode.__init__(self,s)
        self.bits = self.as13().bits
    def int2char(self,n):
        if n==10:
            rval = "X"
        else:
            rval = "%s" % n
        if len(rval) > 1:
            msg = "%s: Internal error" % self.type
            raise ProductCodeError(msg)
        return rval
    def as13(self):
        s = "978-%s*" % self.s[:-1]
        return ISBN13(s)
class ISMN(ProductCode):
    # I don't think there is an ISMN-13
    # But maybe we need to define one in case user inputs the EAN-13
    # or if the scanner needs to understand it. Later.
    def __init__(self,s):
        self.type = "ISMN"
        self.label = "ISMN"
        self.firstCharMap = {"M":3}
        self.lastCharMap = makeCharMap({"*":None})
        self.otherCharMap = makeCharMap({"*":None,"-":"-"," ":" "})
        self.weights=5*[3,1]
        self.magic=10
        ProductCode.__init__(self,s)
        self.bits = self.as13().bits
    def as13(self):
        # The initial "M" becomes a zero here,
        # and we leave the check digit wild.
        # I don't think there really are 13-digit ISMN's.
        # This is only for generating the EAN-13 symbol.
        s = "979-0%s*" % self.s[1:-1]
        return ISMN13(s)
class ISMN13(EAN13):
    # EAN13 version of 10-digit ISMN
    def __init__(self,s):
        self.type = "ISMN13"
        self.label = "ISMN"
        EAN13.__init__(self,s)
        if not s[0] in "9*" or \
           not s[1] in "7*" or \
           not s[2] in "9*":
            msg = "%s: must begin with 979" % self.type
            raise ProductCodeError(msg)



def makeProductCode(s,forceISBN13=True,forceISMN13=False):


    if forceISMN13:
        msg = "there is no ISMN13 yet."
        raise ProductCodeError(msg)
    msgs = []
    rval = None
    
    try:
        return ISBN13(s)
    except ProductCodeError:
        pass
    
    try:
        rval = ISBN10(s)
    except ProductCodeError:
        pass
        
    if rval and forceISBN13:
        try:
            return rval.as13()
        except ProductCodeError:
            pass
    elif rval:
        return rval

    try:
        rval = ISMN(s)
        if forceISMN13:
            return rval.as13()
        else:
            return rval
    except ProductCodeError:
        pass

    try:
        return EAN13(s)
    except ProductCodeError:
        pass

    raise ProductCodeError()


if __name__=="__main__":

    MYNAME="productcode.py"
    MYVERSION="1.0"
    COPYRIGHT="(C) 1999-2007 J. Milgram"
    VERSIONDATE = "Jan 2007"
    MAINTAINER = "bookland-bugs@cgpp.com"

    tests =  [ "0-9669553-0-7",
               "-9669553-0-7",
               "0-9669553-0-",
               "096695530-*",
               "0-9669553-0-8",
               "0-9669553-0-*",
               "0-9*69553-0-7",
               "*-9669553-0---7",
               "M-9669553-0-*",
               "978-0-9669553-0-9",
               "978-0-9669553-0-*",
               "978-0-9669553-*-9",
               "978-0-966955*-0-9",
               "978-0-96695*3-0-9",
               "978-0-9669*53-0-9",
               "978-0-966*553-0-9",
               "978-0-96*9553-0-9",
               "978-0-9*69553-0-9",
               "978-0-*669553-0-9",
               "978-*-9669553-0-9",
               "97*-0-9669553-0-9",
               "9*8-0-9669553-0-9",
               "*78-0-9669553-0-9",
               "979-0-9669553-0-9",
               "979-0-9669553-0-*",
               "979-0-9669553-*-8",
               "979-0-966955*-0-8",
               "979-0-96695*3-0-8",
               "979-0-9669*53-0-8",
               "979-0-966*553-0-8",
               "979-0-96*9553-0-8",
               "979-0-9*69553-0-8",
               "979-0-*669553-0-8",
               "979-*-9669553-0-8",
               "97*-0-9669553-0-8",
               "9*8-0-9669553-0-8",
               "*78-0-9669553-0-8",
               "*78-0-9669553-0-*",
               "90000",
               "9000*",
               "51595" ]

    for s in tests:
        try:
            a = makeProductCode(s)
            print(s,"is valid as",a)
        except ProductCodeError as e:
            print("%s invalid" % s)

    for s in tests:
        try:
            a = makeProductCode(s)
            print(a.bits)
        except ProductCodeError as e:
            pass

