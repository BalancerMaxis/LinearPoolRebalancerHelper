from brownie import (
    interface,
    accounts,
    chain,
    Contract
)
from dotmap import DotMap

VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"

LINEAR_POOLS = DotMap({
    "bbaWETH":"0x60D604890feaa0b5460B28A424407c24fe89374a",
    })
REBALANCER_CONTRACT = DotMap({
    "bbaWETH": "0x9c2fC986b718121bB2DE314351A77681a89b24C2",
    })
account = accounts[0]
linearPool = Contract(LINEAR_POOLS["bbaWETH"])
mainToken = Contract(linearPool.getMainToken())
vault = Contract(VAULT)
vault.getPoolTokenInfo(linearPool.getPoolId(),mainToken)[0]
mainTokenBalance = vault.getPoolTokenInfo(linearPool.getPoolId(),mainToken)[0]
(lowerTarget, upperTarget) = linearPool.getTargets()
rb=Contract(REBALANCER_CONTRACT.bbaWETH)
if mainTokenBalance > upperTarget:
    rb.rebalance(account,{'from': account})
