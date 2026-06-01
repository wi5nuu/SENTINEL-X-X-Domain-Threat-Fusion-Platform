// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ResponseLog {
    struct OperatorAction {
        bytes32 incidentId;
        address operatorAddress;
        string actionType;
        string rationale;
        bytes32 dataHash;
        uint256 timestamp;
    }

    OperatorAction[] public actions;
    mapping(address => bool) public authorized;

    event ActionLogged(bytes32 indexed incidentId, address indexed operator, string actionType, uint256 timestamp);
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

    function logAction(
        bytes32 _incidentId,
        string calldata _actionType,
        string calldata _rationale,
        bytes32 _dataHash
    ) external onlyAuthorized {
        actions.push(OperatorAction({
            incidentId: _incidentId,
            operatorAddress: msg.sender,
            actionType: _actionType,
            rationale: _rationale,
            dataHash: _dataHash,
            timestamp: block.timestamp
        }));
        emit ActionLogged(_incidentId, msg.sender, _actionType, block.timestamp);
    }

    function getActionCount() external view returns (uint256) {
        return actions.length;
    }

    function getAction(uint256 index) external view returns (OperatorAction memory) {
        require(index < actions.length, "Index out of bounds");
        return actions[index];
    }

    function getIncidentActions(bytes32 _incidentId) external view returns (OperatorAction[] memory) {
        uint256 count = 0;
        for (uint i = 0; i < actions.length; i++) {
            if (actions[i].incidentId == _incidentId) {
                count++;
            }
        }
        OperatorAction[] memory result = new OperatorAction[](count);
        uint256 idx = 0;
        for (uint i = 0; i < actions.length; i++) {
            if (actions[i].incidentId == _incidentId) {
                result[idx] = actions[i];
                idx++;
            }
        }
        return result;
    }
}
