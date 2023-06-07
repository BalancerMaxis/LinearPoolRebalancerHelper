from brownie import (
    interface,
    accounts,
    chain,
    Contract
)
from dotmap import DotMap
## Constants from etherscan
VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"

LINEAR_POOLS = DotMap({
    "bbaWETH":"0x60D604890feaa0b5460B28A424407c24fe89374a",
    })
REBALANCER_CONTRACT = DotMap({
    "bbaWETH": "0x9c2fC986b718121bB2DE314351A77681a89b24C2",
    })

## Derived constants
account = accounts[0]
linearPool = Contract(LINEAR_POOLS["bbaWETH"])
mainToken = Contract(linearPool.getMainToken())
vault = Contract(VAULT)
vault.getPoolTokenInfo(linearPool.getPoolId(),mainToken)[0]
mainTokenBalance = vault.getPoolTokenInfo(linearPool.getPoolId(),mainToken)[0]
(lowerTarget, upperTarget) = linearPool.getTargets()
rebalancer=Contract(REBALANCER_CONTRACT.bbaWETH)
## Fuck around and find out
threshhold = 0
## Logic
if mainTokenBalance + threshhold > upperTarget or mainTokenBalance - threshhold < lowerTarget:
    rebalancer.rebalance(account,{'from': account})