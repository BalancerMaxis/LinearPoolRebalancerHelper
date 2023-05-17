import brownie
import time
from brownie import chain
import pytest
import random

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

def test_deploy(deploy):
    return

def test_set_recipient_list(injector, admin, streamer):
    recipients = [streamer]
    amounts = [100]
    periods = [3]
    injector.setRecipientList(recipients, amounts, periods, {"from": admin})
    assert injector.getWatchList() == recipients
    assert injector.getAccountInfo(recipients[0]) == (True, 100, 3, 0, 0)


def test_can_call_check_upkeep(upkeep_caller, injector, streamer, admin):
    # Arrange
    injector.setRecipientList([streamer.address], [100], [2], {"from": admin})
    upkeepNeeded, performData = injector.checkUpkeep.call(
        "",
        {"from": upkeep_caller},
    )
    assert isinstance(upkeepNeeded, bool)
    assert isinstance(performData, bytes)


def test_integration_perform_upkeep_flows(injector, upkeep_caller, streamer, token, admin, whale, gauge,weekly_incentive):
    ## Setup [2] for 2 rounds
    assert token.balanceOf(injector) == 0
    token.transfer(injector, weekly_incentive*3, {"from": admin}) # Tokens for 3 rounds so we are stopped by max rounds in the injector config
    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    reward_data = streamer.reward_data(token)
    ## Advance to the next Epoch
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    if upkeepNeeded is False:
        sleep_time = (reward_data[1] - chain.time())  # about 1 block after the peroiod ends.
        chain.sleep(sleep_time)
        chain.mine()
        (upkeepNeeded, performData) = injector.checkUpkeep(
            "",
            {"from": upkeep_caller},
        )
        assert(upkeepNeeded is True)
    ## Test perform upkeep for the first round
    initial_streamer_balance = token.balanceOf(streamer)
    initial_gauge_balance = token.balanceOf(gauge)
    initial_system_balance = initial_gauge_balance + initial_streamer_balance
    assert(token.balanceOf(injector) >= weekly_incentive)  # injector should have coinz
    assert(injector.performUpkeep(performData, {"from": upkeep_caller})) # Perform upkeep
    ### On this action the streamer seems to send many of it's current tokens to the gauge, but not all.
    sent_to_gauge = token.balanceOf(gauge) - initial_gauge_balance
    leftovers = sent_to_gauge - initial_streamer_balance
    assert(token.balanceOf(streamer) + leftovers == weekly_incentive)  # Tokens are in place
    assert(initial_system_balance + weekly_incentive == token.balanceOf(gauge) + token.balanceOf(streamer)) #no tokens vanished
    ## advance time and check that claim reduces streamer balancer
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    assert(upkeepNeeded==False)  ## not time yet
    r1_streamer_balance = token.balanceOf(streamer)
    chain.mine()
    chain.sleep(300)
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("",{"from": ZERO_ADDRESS})
    assert(upkeepNeeded == False) # not time yet
    claim = gauge.claim_rewards({"from": whale})
    assert(token.balanceOf(streamer) < r1_streamer_balance)  # Whale pulled tokens from streamer on claim

    # sleep till second epoch
    chain.sleep(60*60*24*8) # 8 days should be more than a 1 week epoch
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("",{"from": ZERO_ADDRESS})
    assert(upkeepNeeded == True)
    # Test second upkeep
    initial_system_balance  = token.balanceOf(streamer) + token.balanceOf(gauge)
    assert(injector.performUpkeep(performData, {"from": upkeep_caller})) # Perform upkeep
    assert ( (token.balanceOf(streamer) + token.balanceOf(gauge)) - initial_system_balance == weekly_incentive)  # injector should have new coinz
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": ZERO_ADDRESS})
    assert (upkeepNeeded == False)  # not time yet

    #check third epcoh we stop
    chain.sleep(60 * 60 * 24 * 8)  # 8 days should be more than a 1 week epoch
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": ZERO_ADDRESS})
    assert (upkeepNeeded == False)  # No more runs



def test_pause_and_unpause(injector, admin, upkeep_caller):
    # Pause the contract
    injector.pause({"from": admin})
    assert injector.paused({"from": admin}) is True

    # Wait for the minimum wait period and trigger injection (should fail due to pause)
    chain.sleep(injector.getMinWaitPeriodSeconds())
    with brownie.reverts("Pausable: paused"):
        injector.checkUpkeep("")

    # Unpause the contract
    injector.unpause({"from": admin})
    assert injector.paused({"from": admin}) is False


def test_wont_run_to_soon(injector, upkeep_caller, token, streamer, gauge, weekly_incentive, admin):
    ## Advance to beginning of the next epoch
    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    token.transfer(injector, weekly_incentive*2, {"from": admin})
    reward_data = streamer.reward_data(token)
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    if upkeepNeeded is False:
        sleep_time = (reward_data[1] - chain.time())  # about 1 block after the peroiod ends.
        chain.sleep(sleep_time)
        chain.mine()
        (upkeepNeeded, performData) = injector.checkUpkeep(
            "",
            {"from": upkeep_caller},
        )
        assert(upkeepNeeded is True)
    ## Test perform upkeep for the first round
    initial_streamer_balance = token.balanceOf(streamer)
    initial_gauge_balance = token.balanceOf(gauge)
    initial_system_balance = initial_gauge_balance + initial_streamer_balance
    assert(token.balanceOf(injector) >= weekly_incentive)  # injector should have coinz
    assert(injector.performUpkeep(performData, {"from": upkeep_caller})) # Perform upkeep
    ## Start test
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    initial_system_balance = token.balanceOf(streamer) + token.balanceOf(gauge)
    reward_data = streamer.reward_data(token)
    (distributor, period_finished, rate, duration, received, paid) = reward_data
    sleep_time = random.randint(1, 60*60*24*6)
    chain.sleep(sleep_time)
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    assert not upkeepNeeded
    (distributor, period_finished, rate, duration, received, paid) = reward_data
    sleep_time = (period_finished+1) - chain.time()
    chain.sleep(sleep_time)
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    assert upkeepNeeded


def test_long_upkeep_delay(token, streamer, injector, upkeep_caller, weekly_incentive, gauge, admin, whale):
    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    token.transfer(injector, 1000*10**18*2, {"from": admin})
    reward_data = streamer.reward_data(token)
    ## Advance to the next Epoch
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    if upkeepNeeded is False:
        sleep_time = (reward_data[1] - chain.time())  # about 1 block after the peroiod ends.
        chain.sleep(sleep_time)
        chain.mine()
        (upkeepNeeded, performData) = injector.checkUpkeep(
            "",
            {"from": upkeep_caller},
        )
        assert (upkeepNeeded is True)
    ## Test perform upkeep for the first round
    initial_streamer_balance = token.balanceOf(streamer)
    initial_gauge_balance = token.balanceOf(gauge)
    assert (token.balanceOf(injector) >= weekly_incentive)  # injector should have coinz
    chain.sleep(random.randint(60*60*4, 60*60*24*365))  # random sleep between 4 hours and 1 year
    chain.mine()
    assert (injector.performUpkeep(performData, {"from": upkeep_caller}))  # Perform upkeep
    ## advance time and check that claim reduces streamer balancer
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    assert (upkeepNeeded == False)  ## not time yet
    r1_streamer_balance = token.balanceOf(streamer)
    chain.mine()
    chain.sleep(300)
    chain.mine()
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": ZERO_ADDRESS})
    assert (upkeepNeeded == False)  # not time yet
    claim = gauge.claim_rewards({"from": whale})
    assert (token.balanceOf(streamer) < r1_streamer_balance)  # Whale pulled tokens from streamer on claim

def test_too_short_upkeep_delay(streamer, injector, upkeep_caller, token, weekly_incentive, gauge, admin):
    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    token.transfer(injector, 1000*10**18*2, {"from": admin})
    reward_data = streamer.reward_data(token)
    ## Advance to the next Epoch
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    if upkeepNeeded is False:
        sleep_time = (reward_data[1] - chain.time())  # about 1 block after the peroiod ends.
        chain.sleep(sleep_time)
        chain.mine()
        (upkeepNeeded, performData) = injector.checkUpkeep(
            "",
            {"from": upkeep_caller},
        )
        assert (upkeepNeeded is True)
    ## Test perform upkeep for the first round
    initial_streamer_balance = token.balanceOf(streamer)
    initial_gauge_balance = token.balanceOf(gauge)
    assert (token.balanceOf(injector) >= weekly_incentive)  # injector should have coinz
    assert (injector.performUpkeep(performData, {"from": upkeep_caller}))  # Perform upkeep
    chain.sleep(random.randint(1, 60*60*24*7 - 1)) # Between 1 second and 1 second less than 1 week
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    assert upkeepNeeded is False

def check_funky_upkeep_data(streamer, injector, upkeep_caller, token, weekly_incentive, gauge, admin):
    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    reward_data = streamer.reward_data(token)
    token.transfer(injector, 1000*10**18*2, {"from": admin})
    ## Advance to the next Epoch
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    if upkeepNeeded is False:
        sleep_time = (reward_data[1] - chain.time())  # about 1 block after the peroiod ends.
        chain.sleep(sleep_time)
        chain.mine()
        (upkeepNeeded, performData) = injector.checkUpkeep(
            "",
            {"from": upkeep_caller},
        )
        assert (upkeepNeeded is True)

    injector.setRecipientList([streamer.address], [weekly_incentive], [2], {"from": admin})
    reward_data = streamer.reward_data(token)
    (upkeepNeeded, performData) = injector.checkUpkeep("", {"from": upkeep_caller})
    abi_data = injector.decode(performData)
    assert(False)


def test_sweep(admin, injector, token, deployer):
    system_balance = token.balanceOf(admin) + token.balanceOf(injector)
    admin_balance = token.balanceOf(admin)
    assert token.balanceOf(admin) > 0
    token.transfer(injector, token.balanceOf(admin), {"from": admin})
    assert token.balanceOf(admin) == 0
    injector.sweep(token, admin, {"from": admin})
    assert token.balanceOf(admin) >= admin_balance
    assert token.balanceOf(admin) + token.balanceOf(injector) == system_balance
    with brownie.reverts("Only callable by owner"):
        injector.sweep(deployer, injector, {"from": deployer})

