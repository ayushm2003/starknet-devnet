"""
Contains code for wrapping StarknetContract instances.
"""

from dataclasses import dataclass
from typing import List

from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.utils.api_utils import cast_to_felts

from starknet_devnet.util import Choice

@dataclass
class ContractWrapper:
    """
    Wraps a StarknetContract, storing its types and code for later use.
    """
    def __init__(self, contract: StarknetContract, contract_definition: ContractDefinition):
        self.contract: StarknetContract = contract
        self.contract_definition = contract_definition.remove_debug_info().dump()

        self.code: dict = {
            "abi": contract_definition.abi,
            "bytecode": self.contract_definition["program"]["data"]
        }

    # pylint: disable=too-many-arguments
    async def call_or_invoke(
        self,
        choice: Choice,
        entry_point_selector: int,
        calldata: List[int],
        signature: List[int],
        caller_address: int,
        max_fee: int
    ):
        """
        Depending on `choice`, performs the call or invoke of the function
        identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """

        state = self.contract.state.copy() if choice == Choice.CALL else self.contract.state

        execution_info = await state.invoke_raw(
            contract_address=self.contract.contract_address,
            selector=entry_point_selector,
            calldata=calldata,
            caller_address=caller_address,
            max_fee=max_fee,
            signature=signature and cast_to_felts(values=signature),
        )

        result = list(map(hex, execution_info.call_info.retdata))
        return result, execution_info
