'use strict';

// CLI tests deliberately replace HOME/USERPROFILE to prove they never touch a
// real user profile. liboqs-python interprets that isolated home as a missing
// native installation and otherwise clones/builds liboqs during an ordinary
// test run. Keep the suite hermetic; dedicated PQC tests exercise liboqs.
process.env.SCBE_FORCE_SKIP_LIBOQS = '1';
