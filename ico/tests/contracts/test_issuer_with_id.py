"""Payment forwarder."""
import pytest
import datetime

from ethereum.tester import TransactionFailed
from web3.contract import Contract


@pytest.fixture
def issuer_token(chain, team_multisig) -> Contract:
    """Create the token contract."""

    args = [team_multisig, "Foobar", "FOOB", 1000000, 0, int((datetime.datetime(2017, 4, 22, 16, 0) - datetime.datetime(1970, 1, 1)).total_seconds())]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('CentrallyIssuedToken', deploy_args=args, deploy_transaction=tx)

    contract.transact({"from": team_multisig}).releaseTokenTransfer()
    return contract

@pytest.fixture
def issuer_id_1() -> int:
    return int(1)

@pytest.fixture
def issuer_id_2() -> int:
    return int(2)

@pytest.fixture
def issue_script_owner(accounts):
    """Ethereum account that interacts with issuer contract."""
    return accounts[8]


@pytest.fixture
def issuer_with_id(chain, team_multisig, issuer_token, issue_script_owner):
    args = [issue_script_owner, team_multisig, issuer_token.address]

    tx = {
        "from": team_multisig
    }

    contract, hash = chain.provider.deploy_contract('IssuerWithId', deploy_args=args, deploy_transaction=tx)

    # Set issuance allowance
    assert issuer_token.call().balanceOf(team_multisig) > 2000
    issuer_token.transact({"from": team_multisig}).approve(contract.address, 2000)

    return contract


def test_issuer_with_id(web3, issuer_with_id, issue_script_owner, customer, issuer_token, team_multisig, issuer_id_1):
    """Issue some tokens."""

    team_multisig_begin = issuer_token.call().balanceOf(team_multisig)
    assert issuer_token.call().allowance(team_multisig, issuer_with_id.address) == 2000
    assert issuer_with_id.call().owner() == issue_script_owner
    issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 1000, issuer_id_1)
    assert issuer_with_id.call().issuedCount() == 1000
    assert issuer_token.call().balanceOf(customer) == 1000
    team_multisig_end = issuer_token.call().balanceOf(team_multisig)
    assert team_multisig_begin - team_multisig_end == 1000


def test_issuer_with_different_ids(web3, issuer_with_id, issue_script_owner, customer, issuer_id_1, issuer_id_2):
    """Issue some tokens."""
    issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 500, issuer_id_1)
    issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 500, issuer_id_2)


def test_issuer_with_id_too_many(web3, issuer_with_id, issue_script_owner, customer, issuer_id_1):
    """Issue over allowance."""
    with pytest.raises(TransactionFailed):
        issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 3000, issuer_id_1)


def test_issuer_with_id_twice(web3, issuer_with_id, issue_script_owner, customer, issuer_id_1):
    """Issue some tokens."""
    issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 500, issuer_id_1)
    with pytest.raises(TransactionFailed):
        issuer_with_id.transact({"from": issue_script_owner}).issue(customer, 500, issuer_id_1)


def test_issuer_with_id_not_an_owner(web3, issuer_with_id, customer, issuer_id_1):
    """Somebody tries to issue for themselves."""
    with pytest.raises(TransactionFailed):
        issuer_with_id.transact({"from": customer}).issue(customer, 500, issuer_id_1)
