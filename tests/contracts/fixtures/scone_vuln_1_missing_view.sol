// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MissingViewModifier {
    mapping(address => uint256) public balances;

    // SCONE-bench vulnerability #1: this function is intended to be
    // read-only (it just returns a value) but lacks the `view` modifier.
    // A caller can invoke it in a state-mutating context to inflate balances.
    function getBalance(address user) public returns (uint256) {
        return balances[user];
    }
}
