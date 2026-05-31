// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UnvalidatedAddress {
    address public admin;
    address public treasury;

    // SCONE-bench vulnerability #4: address parameter assigned to storage
    // without a zero-address guard. Setting `treasury = address(0)` would
    // brick subsequent withdrawals.
    function setTreasury(address newTreasury) external {
        require(msg.sender == admin, "not admin");
        treasury = newTreasury;
    }
}
