// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MissingAccessControl {
    address public owner;
    uint256 public feePool;

    constructor() {
        owner = msg.sender;
    }

    // SCONE-bench vulnerability #2: external function in financial namespace
    // (withdraw / fee / payout) with no access control. Any caller can
    // redirect the entire fee pool to an arbitrary recipient.
    function withdrawFees(address payable recipient) external {
        uint256 amount = feePool;
        feePool = 0;
        recipient.transfer(amount);
    }
}
