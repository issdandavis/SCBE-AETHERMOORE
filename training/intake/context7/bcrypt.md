# bcrypt (Node.js)
> Source: Context7 MCP | Category: cyber
> Fetched: 2026-04-04

### Basic Password Hashing with bcrypt

Source: https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md

This JavaScript snippet demonstrates the basic usage of the bcrypt library to hash a password. The hash is generated asynchronously.

```javascript
const bcrypt = require('bcrypt');
const saltRounds = 10;
const myPassword = 'password123';

bcrypt.hash(myPassword, saltRounds, function(err, hash) {
    // Store hash in your DB.
    console.log(hash);
});
```

---

### Async Password Hashing (Promises)

Source: https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md

Demonstrates asynchronous password hashing using bcrypt.js with Promises, suitable for use with .then().

```javascript
bcrypt.hash(myPlaintextPassword, saltRounds).then(function(hash) {
    // Store hash in your password DB.
});
```

---

### Async Password Hashing (Callback)

Source: https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md

Demonstrates how to hash a password asynchronously using bcrypt.js with callbacks. Shows two techniques: generating a salt separately and auto-generating a salt.

```javascript
const bcrypt = require('bcrypt');
const saltRounds = 10;
const myPlaintextPassword = 's0/\/\P4$$w0rD';

// Technique 1: Generate salt separately
bcrypt.genSalt(saltRounds, function(err, salt) {
    bcrypt.hash(myPlaintextPassword, salt, function(err, hash) {
        // Store hash in your password DB.
    });
});

// Technique 2: Auto-generate salt
bcrypt.hash(myPlaintextPassword, saltRounds, function(err, hash) {
    // Store hash in your password DB.
});
```

---

### Async Password Comparison (Callback)

Source: https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md

Shows how to compare a plaintext password against a stored hash asynchronously using bcrypt.js with callbacks.

```javascript
// Load hash from your password DB.
bcrypt.compare(myPlaintextPassword, hash, function(err, result) {
    // result == true
});
bcrypt.compare(someOtherPlaintextPassword, hash, function(err, result) {
    // result == false
});
```

---

### ESM Import and Usage

Source: https://github.com/kelektiv/node.bcrypt.js/blob/master/README.md

Demonstrates how to import and use bcrypt.js with ECMAScript Modules (ESM) syntax, including async/await for password comparison.

```javascript
import bcrypt from "bcrypt";

// later
await bcrypt.compare(password, hash);
```
