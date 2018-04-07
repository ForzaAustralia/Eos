#   Eos - Verifiable elections
#   Copyright © 2017  RunasSudo (Yingtong Li)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from eos.core.bigint import *
from eos.core.objects import *
from eos.core.hashing import *

class BitStream(EosObject):
	def __init__(self, value=None, nbits=None):
		if value:
			self.impl = value
			self.nbits = nbits if nbits else self.impl.nbits()
		else:
			self.impl = ZERO
			self.nbits = 0
		self.ptr = 0
		self.remaining = self.nbits
	
	def seek(self, ptr):
		self.ptr = ptr
		self.remaining = self.nbits - self.ptr
	
	def read(self, nbits=None):
		# 11000110110
		#    ^----
		if nbits is None:
			nbits = self.remaining
		if nbits > self.remaining:
			raise Exception('Not enough bits to read from BitString')
		
		val = (self.impl >> (self.remaining - nbits)) & ((ONE << nbits) - ONE)
		self.ptr += nbits
		self.remaining -= nbits
		return val
	
	def write(self, bits, nbits=None):
		# 11     0100110
		#   10010
		#   ^----
		if nbits is None:
			nbits = bits.nbits()
		if nbits < bits.nbits():
			raise Exception('Too many bits to write to BitString')
		
		self.impl = ((self.impl >> self.remaining) << (self.remaining + nbits)) | (bits << self.remaining) | (self.impl & ((ONE << self.remaining) - 1))
		self.ptr += nbits
		self.nbits += nbits
	
	# Append to the end without affecting ptr
	def append(self, bits, nbits=None):
		if nbits is None:
			nbits = bits.nbits()
		if nbits < bits.nbits():
			raise Exception('Too many bits to append to BitString')
		
		self.impl = (self.impl << nbits) | bits
		self.nbits += nbits
		self.remaining += nbits
	
	def read_bigint(self):
		length = self.read(32)
		length = length.__int__()
		return self.read(length)
	
	def write_bigint(self, value):
		self.write(BigInt(value.nbits()), 32) # TODO: Arbitrary lengths
		self.write(value)
		return self
	
	def read_string(self):
		length = self.read(32)
		length = length.__int__() # JS attempts to call this twice if we do it in one line
		
		if is_python:
			ba = bytearray()
			for i in range(length):
				ba.append(int(self.read(7)))
			return ba.decode('ascii')
		else:
			ba = []
			for i in range(length):
				val = self.read(7)
				val = val.__int__()
				ba.append(val)
			return String.fromCharCode(*ba)
	
	def write_string(self, strg):
		self.write(BigInt(len(strg)), 32) # TODO: Arbitrary lengths
		
		# TODO: Support non-ASCII encodings
		if is_python:
			ba = strg.encode('ascii')
			for i in range(len(strg)):
				self.write(BigInt(ba[i]), 7)
		else:
			for i in range(len(strg)):
				self.write(BigInt(strg.charCodeAt(i)), 7)
		
		return self
	
	def pad_by(self, padding_size, pad_at_end=False):
		if padding_size > 0:
			if pad_at_end:
				# Suitable for structured data
				self.seek(self.nbits)
				self.write(ZERO, padding_size)
			else:
				# Suitable for raw numbers
				self.nbits += padding_size
		return self # For convenient chaining
	
	def pad_to(self, target_size, pad_at_end=False):
		if self.nbits < target_size:
			diff = target_size - self.nbits
			self.pad_by(diff, pad_at_end)
		return self
	
	# Make the size of this BitStream a multiple of the block_size
	def multiple_of(self, block_size, pad_at_end=False):
		if self.nbits % block_size != 0:
			diff = block_size - (self.nbits % block_size)
			self.pad_by(diff, pad_at_end)
		return self
	
	def map(self, func, block_size):
		if self.nbits % block_size != 0:
			raise Exception('The size of the BitStream must be a multiple of block_size')
		
		self.seek(0)
		result = []
		while self.remaining > 0:
			result.append(func(self.read(block_size)))
		return result
	
	@classmethod
	def unmap(cls, value, func, block_size):
		bs = cls()
		for item in value:
			bs.write(func(item), block_size)
		bs.seek(0)
		return bs
	
	def serialise(self, options=SerialiseOptions.DEFAULT):
		return self.impl
	
	@classmethod
	def deserialise(cls, value):
		return cls(value)

class InfiniteHashBitStream(BitStream):
	def __init__(self, seed):
		self.sha = SHA256()
		self.sha.update_bigint(seed)
		self.ctr = 0
		self.sha.update_text(str(self.ctr))
		
		super().__init__(self.sha.hash_as_bigint(), self.sha.nbits)
	
	def read(self, nbits=None):
		# 11000110110
		#    ^----
		if nbits is None:
			raise Exception('Cannot read indefinite amount from InfiniteHashBitStream')
		while nbits > self.remaining:
			self.ctr += 1
			self.sha.update_text(str(self.ctr))
			self.append(self.sha.hash_as_bigint(), self.sha.nbits)
		return super().read(nbits)
