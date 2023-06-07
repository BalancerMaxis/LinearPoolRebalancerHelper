// SPDX-License-Identifier: MIT

pragma solidity 0.8.19;

import "@chainlink/contracts/src/v0.8/ConfirmedOwner.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "interfaces/balancer/solidity-utils/openzeppelin/SafeERC20.sol";
import "interfaces/balancer/solidity-utils/openzeppelin/IERC20.sol";
import "interfaces/balancer/vault/IVault.sol";
import "interfaces/balancer/pool-linear/ILinearPool.sol";

interface ILinearPoolRebalancer {
    function rebalance(address recipient) external returns (uint256);
    function rebalanceWithExtraMain(address recipient, uint256 extraMain) external returns (uint256);
}

/**
 * @title Linear Pool Rebalancer Keeper
 * @author zen-dragon & tritium
 * @notice Chainlink automation compatable smart contract to handle rebalancing linear pools.
 */
contract LinearPoolRebalancer is ConfirmedOwner, Pausable {
  event keeperRegistryUpdated(address oldAddress, address newAddress);
  event poolRebalanced(address pool, IERC20[] tokens, uint256 amount, bool half);
  event poolListUpdated(LinearPoolInfo[]);

struct LinearPoolInfo {
  address poolAddress;
  address rebalancerAddress;
 }

LinearPoolInfo[] public linearPools;

  // Storage variables 
  address public keeperRegistry;
  LinearPoolInfo[] public poolRegistry;
  IVault constant public vault = IVault();
  uint256 public threshold;

  /*
  * A map of ILinearPoolRebalancers by LinearPoolTokenAddress 
  * Need to be able to extract list of linear pool token addresses
  bytes constant emptyBytes  = bytes("");
  */

    function setPoolWatchList(
    LinearPoolInfo[] calldata poolInfos
  ) external onlyOwner {
      emit poolListUpdated(poolInfos);
      poolRegistry = poolInfos;
  }

  /**
   * @notice Get list of addresses that are underfunded and return keeper-compatible payload
   * @return rebalanceNeeded signals if upkeep is needed, performData is an abi encoded list of rebalancer contracts that will trigger a rebalance
   */
function checkUpkeep(bytes calldata) external view override whenNotPaused returns (bool rebalanceNeeded, bytes memory performData) {
  LinearPoolInfo[] memory poolInfos = poolRegistry;
  address[] memory needsRebalancing = new address[](poolInfos.length);
  uint256 count = 0;

  for (uint256 i = 0; i < poolInfos.length; i++) {
    ILinearPool lp = ILinearPool(poolInfos[i].poolAddress());
    (uint256 lowerTarget, uint256 upperTarget) = lp.getTargets();
    IERC20 mainToken = IERC20(lp.getMainToken());
    uint256 mainTokenBalance = vault.getPoolTokenInfo(lp.getPoolId(), mainToken).cash;

    if (mainTokenBalance + threshold > upperTarget || mainTokenBalance - threshold < lowerTarget) {
      needsRebalancing[count] = lp.getPoolAddress();
      count++;
    }
  }

  // Trim the array to the correct length
  address[] memory rebalancingAddresses = new address[](count);
  for (uint256 i = 0; i < count; i++) {
    rebalancingAddresses[i] = needsRebalancing[i];
  }

  rebalanceNeeded = count > 0;
  performData = abi.encode(rebalancingAddresses);
  return (rebalanceNeeded, performData);
}


  
  /**
   * @notice Called by keeper to send funds to underfunded addresses
   * @param performData The abi encoded list of addresses to fund
   */
  function performUpkeep(bytes calldata performData) external override onlyKeeperRegistry whenNotPaused {
    address[] memory needsFunding = abi.decode(performData, (address[]));
    rebalanceLinearPool(needsFunding);
  }

  /**
   * @notice Withdraws the contract balance
   * @param amount The amount of eth (in wei) to withdraw
   * @param payee The address to pay
   */
  function withdraw(uint256 amount, address payable payee) external onlyOwner {
    if (payee == address(0)) {
      revert("zero address");
    }
    payee.transfer(amount);
  }

  /**
   * @notice Sweep the full contract's balance for a given ERC-20 token
   * @param token The ERC-20 token which needs to be swept
   * @param payee The address to pay
   */
  function sweep(address token, address payee) external onlyOwner {
    uint256 balance = IERC20(token).balanceOf(address(this));
    emit ERC20Swept(token, payee, balance);
    SafeERC20.safeTransfer(IERC20(token), payee, balance);
  }


   /**
   * @notice Sets the list of fee tokens to operate on
   * @param tokens the list of addresses to distribute
   */
  function setTokens(IERC20[] memory tokens) public onlyOwner {
    require(tokens.length >= 1, "Must provide at least once token");
    emit tokensSet(tokens);
    for(uint i=0; i < tokens.length; i++){
      tokens[i].approve(address(feeDistributor), 2**128);
    }
    managedTokens = tokens;
  }
  /* 
  * setPoolRegistry for new set of pools and rebalancers input is entire datastructure and 
  * new versions fully replace prior data structure. 
  * v2... fancy add and remove one pool and their rebalancer
  * v3... fung schway add and remove lists of pools and their rebalancers
*/ 

/* 
* getter for LinearPools or whatever we determine to be needed 

  /**
   * @notice Sets the keeper registry address
   */
  function setKeeperRegistry(address _keeperRegistry) public onlyOwner {
    emit keeperRegistryUpdated(keeperRegistry, _keeperRegistry);
    keeperRegistry = _keeperRegistry;
  }

  /**
   * @notice Unpauses the contract
   */
  function unpause() external onlyOwner {
    _unpause();
  }

  modifier onlyKeeperRegistry() {
    if (msg.sender != keeperRegistry && msg.sender != owner()) {
      require(false, "Only the Registry can do that");
    }
    _;
  }


}