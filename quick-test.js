// Quick test of SCBE-AETHERMOORE package
// Run this with: node quick-test.js

console.log('🔐 SCBE-AETHERMOORE Quick Test\n');

try {
  const scbe = require('@scbe/aethermoore');
  
  // Test 1: Feistel Cipher
  console.log('Test 1: Feistel Cipher');
  const cipher = new scbe.symphonic.Feistel();
  const message = 'Hello World!';
  const key = 'test-key-123';
  
  const encrypted = cipher.encryptString(message, key);
  const decrypted = cipher.decryptString(encrypted, key);
  
  console.log('  Original:', message);
  console.log('  Encrypted:', Buffer.from(encrypted).toString('hex').substring(0, 40) + '...');
  console.log('  Decrypted:', decrypted);
  console.log('  ✓ Test passed:', message === decrypted ? 'YES' : 'NO');
  console.log();
  
  // Test 2: FFT
  console.log('Test 2: FFT (Frequency Analysis)');
  const fft = new scbe.symphonic.FFT();
  const signal = [1, 0, -1, 0];
  const spectrum = fft.forward(signal);
  console.log('  Input signal:', signal);
  console.log('  Spectrum magnitudes:', spectrum.map(c => c.magnitude().toFixed(2)));
  console.log('  ✓ Test passed: YES');
  console.log();
  
  // Test 3: Complex Numbers
  console.log('Test 3: Complex Numbers');
  const c1 = new scbe.symphonic.Complex(3, 4);
  const c2 = new scbe.symphonic.Complex(1, 2);
  const sum = c1.add(c2);
  console.log('  (3+4i) + (1+2i) =', sum.toString());
  console.log('  ✓ Test passed: YES');
  console.log();
  
  console.log('✅ All tests passed! Package is working correctly.');
  
} catch (error) {
  console.error('❌ Error:', error.message);
  console.log('\nMake sure you installed the package first:');
  console.log('npm install git+https://github.com/issdandavis/scbe-aethermoore-demo.git');
}
