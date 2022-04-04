"""
Contains code for wrapping StarknetContract instances.
"""

from dataclasses import dataclass
from typing import List

from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo

from starknet_devnet.adapt import adapt_calldata, adapt_output
from starknet_devnet.util import Choice, StarknetDevnetException

DEFAULT_SELECTOR = get_selector_from_name("__default__")

def extract_types(abi):
    """
    Extracts the types (structs) used in the contract whose ABI is provided.
    """

    structs = [entry for entry in abi if entry["type"] == "struct"]
    type_dict = { struct["name"]: struct for struct in structs }
    return type_dict

def extract_function_abis(function_mapping: dict):
    """Extracts ABI of each function."""
    selector2abi = {}
    for method_name in function_mapping:
        selector2abi[get_selector_from_name(method_name)] = function_mapping[method_name]
    return selector2abi

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

        self.types: dict = extract_types(contract_definition.abi)

        # pylint: disable=protected-access
        self.selector2abi: dict = extract_function_abis(self.contract._abi_function_mapping)

    async def call_or_invoke(self, choice: Choice, entry_point_selector: int, calldata: List[int], signature: List[int]):
        """
        Depending on `choice`, performs the call or invoke of the function
        identified with `entry_point_selector`, potentially passing in `calldata` and `signature`.
        """

        if entry_point_selector in self.selector2abi:
            method_abi = self.selector2abi[entry_point_selector]
        elif DEFAULT_SELECTOR in self.selector2abi:
            method_abi = self.selector2abi[DEFAULT_SELECTOR]
        else:
            raise StarknetDevnetException(message=f"Illegal method selector: {entry_point_selector}.")

        method = getattr(self.contract, method_abi["name"])
        adapted_calldata = adapt_calldata(calldata, method_abi["inputs"], self.types)

        prepared = method(*adapted_calldata)
        called = getattr(prepared, choice.value)
        execution_info: StarknetTransactionExecutionInfo = await called(signature=signature)
        return adapt_output(execution_info.result), execution_info
