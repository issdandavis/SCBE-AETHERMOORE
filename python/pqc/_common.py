import importlib


class _CryptoAlg:
	__slots__ = ['_ffi', '_lib', '_new']

	@classmethod
	def _init_module(cls, libname, _globals, /):
		# TODO import optimized implementations
		if libname.startswith('mceliece'):
			libname = libname + 'f'
		module = importlib.import_module(f'pqc._lib.lib{libname}_clean')
		result = cls(module)
		for key in result.__all__:
			_globals[key] = getattr(result, key)
		return cls.__all__

	def __init__(self, module, /):
		self._ffi = module.ffi
		self._lib = module.lib
		self._new = self._ffi.new_allocator(should_clear_after_alloc=False)

	def _from_buffer(self, obj, /):
		return self._ffi.from_buffer('uint8_t[]', obj)

	def _from_buffer_typed(self, t, obj, /):
		result = self._ffi.from_buffer(t, obj)
		if len(result) != len(obj):
			with result:
				raise TypeError(f'bad {t} (expected {len(result)} bytes, got {len(obj)} bytes)')
		return result


class _KemAlg(_CryptoAlg):
	__all__ = ['keypair', 'encap', 'decap']

	def keypair(self):
		with \
			self._new('_CRYPTO_PUBLICKEY_t') as _pk,\
			self._new('_CRYPTO_SECRETKEY_t') as _sk\
		:
			errno = self._lib.crypto_kem_keypair(_pk, _sk)

			if errno == 0:
				return bytes(_pk), bytes(_sk)
			else:
				raise RuntimeError(f'crypto_kem_keypair returned error code {errno}')

	def encap(self, pk):
		with \
			self._new('_CRYPTO_KEM_CIPHERTEXT_t') as _ct,\
			self._new('_CRYPTO_KEM_PLAINTEXT_t') as _ss,\
			self._from_buffer_typed('_CRYPTO_PUBLICKEY_t', pk) as _pk\
		:
			errno = self._lib.crypto_kem_enc(_ct, _ss, _pk)

			if errno == 0:
				return bytes(_ss), bytes(_ct)
			else:
				raise RuntimeError(f'crypto_kem_enc returned error code {errno}')

	def decap(self, ct, sk):
		with \
			self._new('_CRYPTO_KEM_PLAINTEXT_t') as _ss,\
			self._from_buffer_typed('_CRYPTO_KEM_CIPHERTEXT_t', ct) as _ct,\
			self._from_buffer_typed('_CRYPTO_SECRETKEY_t', sk) as _sk\
		:
			errno = self._lib.crypto_kem_dec(_ss, _ct, _sk)

			if errno == 0:
				return bytes(_ss)
			else:
				raise RuntimeError(f'crypto_kem_dec returned error code {errno}')

class _SigAlg(_CryptoAlg):
	__all__ = ['keypair', 'sign', 'verify', 'verify_bool']

	def keypair(self):
		with \
			self._new('_CRYPTO_PUBLICKEY_t') as _pk, \
			self._new('_CRYPTO_SECRETKEY_t') as _sk\
		:
			errno = self._lib.crypto_sign_keypair(_pk, _sk)

			if errno == 0:
				return bytes(_pk), bytes(_sk)
			else:
				raise RuntimeError(f'crypto_sign_keypair returned error code {errno}')

	def sign(self, m, sk):
		with \
			self._new('_CRYPTO_SIGNATURE_t') as _sig,\
			self._new('size_t*') as _siglen,\
			self._from_buffer(m) as _m,\
			self._from_buffer_typed('_CRYPTO_SECRETKEY_t', sk) as _sk\
		:
			errno = self._lib.crypto_sign_signature(_sig, _siglen, _m, len(_m), _sk)

			if errno == 0:
				assert len(_sig) == _siglen[0]  # Fixed-length signature
				return bytes(_sig)
			else:
				raise RuntimeError(f'crypto_sign_signature returned error code {errno}')

	def verify(self, sig, m, pk):
		with \
			self._from_buffer(sig) as _sig,\
			self._from_buffer(m) as _m,\
			self._from_buffer_typed('_CRYPTO_PUBLICKEY_t', pk) as _pk\
		:
			errno = self._lib.crypto_sign_verify(_sig, len(_sig), _m, len(_m), _pk)

			if errno == 0:
				return
			elif errno == -1:
				raise ValueError('verification failed')
			else:
				raise RuntimeError(f'crypto_sign_verify returned error code {errno}')

	def verify_bool(self, sig, m, pk):
		with \
			self._from_buffer(sig) as _sig,\
			self._from_buffer(m) as _m,\
			self._from_buffer_typed('_CRYPTO_PUBLICKEY_t', pk) as _pk\
		:
			errno = self._lib.crypto_sign_verify(_sig, len(_sig), _m, len(_m), _pk)

			# TODO branchless option?
			if errno == 0:
				return True
			elif errno == -1:
				return False
			else:
				raise RuntimeError(f'crypto_sign_verify returned error code {errno}')


class _VarSigAlg(_SigAlg):

	def sign(self, m, sk):
		with \
			self._new('_CRYPTO_SIGNATURE_t') as _sigbuf,\
			self._new('size_t*') as _siglen,\
			self._from_buffer(m) as _m,\
			self._from_buffer_typed('_CRYPTO_SECRETKEY_t', sk) as _sk\
		:
			errno = self._lib.crypto_sign_signature(_sigbuf, _siglen, _m, len(_m), _sk)

			if errno == 0:
				_sig = _sigbuf[0:_siglen[0]]  # Variable-length signature
				return bytes(_sig)
			else:
				raise RuntimeError(f'crypto_sign_signature returned error code {errno}')
