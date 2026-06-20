// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CleanContract {
    address public owner;
    address public treasury;
    mapping(address => uint256) private _balances;

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    // Read-only — correctly marked view.
    function getBalance(address user) public view returns (uint256) {
        return _balances[user];
    }

    // Financial-impact — access-controlled.
    function withdrawFees(address payable recipient) external onlyOwner {
        uint256 amount = _balances[address(this)];
        _balances[address(this)] = 0;
        recipient.transfer(amount);
    }

    // Address setter — zero-address guarded.
    function setTreasury(address newTreasury) external onlyOwner {
        require(newTreasury != address(0), "treasury cannot be zero");
        treasury = newTreasury;
    }

    // Payable function that validates msg.value.
    function deposit() external payable {
        require(msg.value > 0, "deposit requires value");
        _balances[msg.sender] += msg.value;
    }
}
