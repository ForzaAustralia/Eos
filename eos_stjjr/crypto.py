#    Copyright © 2017  RunasSudo (Yingtong Li)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import eos_core.libobjects
import eos_stjjr.bigint

import hashlib

class CyclicGroup(eos_core.libobjects.EosDictObject):
	class EosMeta:
		eos_name = 'eos_stjjr.crypto.CyclicGroup'
		eos_fields = [
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'p'),
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'g'),
		]
	
	@property
	def q(self):
		# p = 2q + 1
		return (p - eos_stjjr.bigint.ONE) / eos_stjjr.bigint.TWO

# RFC 3526
DEFAULT_GROUP = CyclicGroup(
	p=eos_stjjr.bigint.BigInt('FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF', 16),
	g=eos_stjjr.bigint.TWO
)

# Chaum-Pedersen-Signed ElGamal encryption from:
# SEURIN, Yannick and TREGER, Joana. A Robust and Plaintext-Aware Variant of Signed ElGamal Encryption. In: Cryptology ePrint Archive. International Association for Cryptologic Research, 2012 [viewed 2017-01-27]. Revised 2013-02-25. Available from: http://ia.cr/2012/649

class CPSEGPublicKey(eos_core.libobjects.EosDictObject):
	class EosMeta:
		eos_name = 'eos_stjjr.crypto.CPSEGPublicKey'
		eos_fields = [
			eos_core.libobjects.EosField(CyclicGroup, 'group'),
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'X'),
		]
	
	def encrypt(self, message):
		# Choose two elements from Z*p
		r = eos_stjjr.bigint.crypto_random(eos_stjjr.bigint.ONE, self.group.p - eos_stjjr.bigint.ONE)
		a = eos_stjjr.bigint.crypto_random(eos_stjjr.bigint.ONE, self.group.p - eos_stjjr.bigint.ONE)
		# Calculate encryption
		R = pow(self.group.g, r, self.group.p)
		Rp = pow(self.X, r, self.group.p)
		Y = (message * Rp) % self.group.p
		# Calculate signature challenge
		A = pow(self.group.g, a, self.group.p)
		Ap = pow(self.X, a, self.group.p)
		Hc = hashlib.sha256() # TODO: For JS too
		Hc.update(str(Y).encode('ascii'))
		Hc.update(str(R).encode('ascii'))
		Hc.update(str(Rp).encode('ascii'))
		Hc.update(str(A).encode('ascii'))
		Hc.update(str(Ap).encode('ascii'))
		c = eos_stjjr.bigint.BigInt(Hc.hexdigest(), 16) % self.group.p
		# Calculate signature
		# Confusingly, this is not mod p!!!
		s = a + c*r
		
		return CPSEGCiphertext(public_key=self, R=R, Y=Y, A=A, s=s)

class CPSEGPrivateKey(eos_core.libobjects.EosDictObject):
	class EosMeta:
		eos_name = 'eos_stjjr.crypto.CPSEGPrivateKey'
		eos_fields = [
			eos_core.libobjects.EosField(CPSEGPublicKey, 'public_key'),
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'x'),
		]
	
	@staticmethod
	def generate():
		# Choose an element from Z*p
		# Z*p = {1, 2, ..., p-1}
		x = eos_stjjr.bigint.crypto_random(eos_stjjr.bigint.ONE, DEFAULT_GROUP.p - eos_stjjr.bigint.ONE)
		# Calculate the public key as G^x
		X = pow(DEFAULT_GROUP.g, x, DEFAULT_GROUP.p)
		
		pk = CPSEGPublicKey(group=DEFAULT_GROUP, X=X)
		sk = CPSEGPrivateKey(public_key=pk, x=x)
		return sk
	
	def decrypt(self, ciphertext):
		# Calculate signature challenge
		Rp = pow(ciphertext.R, self.x, self.public_key.group.p)
		Ap = pow(ciphertext.A, self.x, self.public_key.group.p)
		Hc = hashlib.sha256() # TODO: For JS too
		Hc.update(str(ciphertext.Y).encode('ascii'))
		Hc.update(str(ciphertext.R).encode('ascii'))
		Hc.update(str(Rp).encode('ascii'))
		Hc.update(str(ciphertext.A).encode('ascii'))
		Hc.update(str(Ap).encode('ascii'))
		c = eos_stjjr.bigint.BigInt(Hc.hexdigest(), 16) % self.public_key.group.p
		# Verify signature
		if pow(self.public_key.group.g, ciphertext.s, self.public_key.group.p) != (ciphertext.A * pow(ciphertext.R, c, self.public_key.group.p)) % self.public_key.group.p:
			raise Exception('Signature is incorrect')
		if pow(self.public_key.X, ciphertext.s, self.public_key.group.p) != (Ap * pow(Rp, c, self.public_key.group.p)) % self.public_key.group.p:
			raise Exception('Signature is incorrect')
		
		# Compute 1/Rp = Rp^-1 = Rp^(p-2), see HAC 2.127(ii)
		Rp_inv = pow(Rp, self.public_key.group.p - eos_stjjr.bigint.TWO, self.public_key.group.p)
		
		return (ciphertext.Y * Rp_inv) % self.public_key.group.p

class EGCiphertext(eos_core.libobjects.EosDictObject):
	class EosMeta:
		eos_name = 'eos_stjjr.crypto.EGCiphertext'
		eos_fields = [
			eos_core.libobjects.EosField(CPSEGPublicKey, 'public_key'),
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'R'), # G^r
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'Y'), # M X^r
		]

class CPSEGCiphertext(EGCiphertext):
	class EosMeta:
		eos_name = 'eos_stjjr.crypto.CPSEGCiphertext'
		eos_fields = EGCiphertext._eosmeta.eos_fields + [
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 'A'),
			eos_core.libobjects.EosField(eos_stjjr.bigint.BigInt, 's'),
		]
