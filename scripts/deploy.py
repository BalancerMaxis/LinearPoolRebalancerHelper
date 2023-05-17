from brownie import (
    interface,
    accounts,
    chain,
    periodicRewardsInjector,
)


account = accounts.load("tmdelegate") #load your account here
ADMIN_ADDRESS = "0xc38c5f97B34E175FFd35407fc91a937300E33860" # Balancer Maxi LM Multisig on mainnet, polygon and arbi
UPKEEP_CALLER_ADDRESS = "0x75c0530885F385721fddA23C539AF3701d6183D4" ## Chainlink Registry on Arbitrum
TOKEN_ADDRESS = "0x912ce59144191c1204e64559fe8253a0e49e6548" # LDO address on Arbiturm


REGISTRY_BY_CHAIN = {
    42161: "0x75c0530885F385721fddA23C539AF3701d6183D4",
    137: "0x02777053d6764996e594c3E88AF1D58D5363a2e6",
}


LINK_BY_CHAIN = {
    42161: "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4"
    137: "0xb0897686c545045aFc77CF20eC7A532E3120E0F1"
}


injector = periodicRewardsInjector.deploy(
    REGISTRY_BY_CHAIN[chain.id],
    60 * 60 * 7,  # minWaitPeriodSeconds is 1 week
    TOKEN_ADDRESS,
    {"from": account},
    publish_source=True
)

injector.transferOwnership(ADMIN_ADDRESS, {"from": account})
