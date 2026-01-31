from .kem import mceliece6960119

if __name__ == '__main__':
	public_key, secret_key = mceliece6960119.keypair()
	test_key, test_ciphertext = mceliece6960119.encap(public_key)
	test_decrypted = mceliece6960119.decap(test_ciphertext, secret_key)

	if test_key != test_decrypted:
		raise AssertionError('fail :(')
	print('OK')
	...
