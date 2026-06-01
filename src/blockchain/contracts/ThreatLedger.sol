// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ThreatLedger {
    struct ThreatEvent {
        bytes32 eventHash;
        uint256 timestamp;
        string threatClass;
        string ipfsCid;
        address submittedBy;
        bytes32 previousHash;
    }

    ThreatEvent[] public events;
    mapping(bytes32 => uint256) public hashToIndex;
    mapping(address => bool) public authorized;

    event EventRecorded(bytes32 indexed eventHash, uint256 timestamp, string threatClass);
    event AuthorizedAddressAdded(address indexed account);
    event AuthorizedAddressRemoved(address indexed account);

    modifier onlyAuthorized() {
        require(authorized[msg.sender], "Not authorized");
        _;
    }

    constructor() {
        authorized[msg.sender] = true;
    }

    function addAuthorizedAddress(address _account) external onlyAuthorized {
        authorized[_account] = true;
        emit AuthorizedAddressAdded(_account);
    }

    function removeAuthorizedAddress(address _account) external onlyAuthorized {
        require(_account != msg.sender, "Cannot remove self");
        authorized[_account] = false;
        emit AuthorizedAddressRemoved(_account);
    }

    function recordEvent(
        bytes32 _eventHash,
        string calldata _threatClass,
        string calldata _ipfsCid
    ) external onlyAuthorized {
        bytes32 prevHash = events.length > 0 ? events[events.length - 1].eventHash : bytes32(0);
        events.push(ThreatEvent({
            eventHash: _eventHash,
            timestamp: block.timestamp,
            threatClass: _threatClass,
            ipfsCid: _ipfsCid,
            submittedBy: msg.sender,
            previousHash: prevHash
        }));
        hashToIndex[_eventHash] = events.length - 1;
        emit EventRecorded(_eventHash, block.timestamp, _threatClass);
    }

    function getEventCount() external view returns (uint256) {
        return events.length;
    }

    function getEvent(uint256 index) external view returns (ThreatEvent memory) {
        require(index < events.length, "Index out of bounds");
        return events[index];
    }

    function verifyChainIntegrity() external view returns (bool) {
        for (uint i = 1; i < events.length; i++) {
            if (events[i].previousHash != events[i - 1].eventHash) return false;
        }
        return true;
    }
}
