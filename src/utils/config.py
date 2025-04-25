from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import yaml
from pathlib import Path
import asyncio


@dataclass
class SettingsConfig:
    THREADS: int
    ATTEMPTS: int
    ACCOUNTS_RANGE: Tuple[int, int]
    EXACT_ACCOUNTS_TO_USE: List[int]
    PAUSE_BETWEEN_ATTEMPTS: Tuple[int, int]
    PAUSE_BETWEEN_SWAPS: Tuple[int, int]
    RANDOM_PAUSE_BETWEEN_ACCOUNTS: Tuple[int, int]
    RANDOM_PAUSE_BETWEEN_ACTIONS: Tuple[int, int]
    BROWSER_PAUSE_MULTIPLIER: float
    RANDOM_INITIALIZATION_PAUSE: Tuple[int, int]
    TELEGRAM_USERS_IDS: List[int]
    TELEGRAM_BOT_TOKEN: str

@dataclass
class FaucetConfig:
    USE_SOLVIUM_FOR_CLOUDFLARE: bool
    SOLVIUM_API_KEY: str

    USE_CAPSOLVER_FOR_CLOUDFLARE: bool
    CAPSOLVER_API_KEY: str

    NOCAPTCHA_API_KEY: str
    PROXY_FOR_NOCAPTCHA: str


@dataclass
class FlowConfig:
    TASKS: List
    NUMBER_OF_SWAPS: Tuple[int, int]
    PERCENT_OF_BALANCE_TO_SWAP: Tuple[int, int]


@dataclass
class AprioriConfig:
    AMOUNT_TO_STAKE: Tuple[float, float]
    STAKE: bool
    UNSTAKE: bool


@dataclass
class MagmaConfig:
    AMOUNT_TO_STAKE: Tuple[float, float]
    STAKE: bool
    UNSTAKE: bool


@dataclass
class KintsuConfig:
    AMOUNT_TO_STAKE: Tuple[float, float]
    STAKE: bool
    UNSTAKE: bool

@dataclass
class DustedConfig:
    CLAIM: bool
    SKIP_TWITTER_VERIFICATION: bool


@dataclass
class NostraConfig:
    PERCENT_OF_BALANCE_TO_DEPOSIT: Tuple[float, float]
    DEPOSIT: bool
    BORROW: bool
    REPAY: bool
    WITHDRAW: bool


@dataclass
class WalletInfo:
    account_index: int
    private_key: str
    address: str
    balance: float
    transactions: int


@dataclass
class WalletsConfig:
    wallets: List[WalletInfo] = field(default_factory=list)


@dataclass
class GaszipConfig:
    NETWORKS_TO_REFUEL_FROM: List[str]
    AMOUNT_TO_REFUEL: Tuple[float, float]
    MINIMUM_BALANCE_TO_REFUEL: float
    WAIT_FOR_FUNDS_TO_ARRIVE: bool
    MAX_WAIT_TIME: int
    BRIDGE_ALL: bool
    BRIDGE_ALL_MAX_AMOUNT: float


@dataclass
class MemebridgeConfig:
    NETWORKS_TO_REFUEL_FROM: List[str]
    AMOUNT_TO_REFUEL: Tuple[float, float]
    MINIMUM_BALANCE_TO_REFUEL: float
    WAIT_FOR_FUNDS_TO_ARRIVE: bool
    MAX_WAIT_TIME: int
    BRIDGE_ALL: bool
    BRIDGE_ALL_MAX_AMOUNT: float

@dataclass
class CrustySwapConfig:
    NETWORKS_TO_REFUEL_FROM: List[str]
    AMOUNT_TO_REFUEL: Tuple[float, float]
    MINIMUM_BALANCE_TO_REFUEL: float
    WAIT_FOR_FUNDS_TO_ARRIVE: bool
    MAX_WAIT_TIME: int
    BRIDGE_ALL: bool
    BRIDGE_ALL_MAX_AMOUNT: float
    SELL_PERCENT_OF_BALANCE: Tuple[int, int]
    SELL_MAXIMUM_AMOUNT: float

@dataclass
class TestnetBridgeConfig:
    NETWORKS_TO_REFUEL_FROM: List[str]
    AMOUNT_TO_REFUEL: Tuple[float, float]
    MINIMUM_BALANCE_TO_REFUEL: float
    WAIT_FOR_FUNDS_TO_ARRIVE: bool
    MAX_WAIT_TIME: int
    BRIDGE_ALL: bool
    BRIDGE_ALL_MAX_AMOUNT: float


@dataclass
class ShmonadConfig:
    PERCENT_OF_BALANCE_TO_SWAP: Tuple[int, int]
    BUY_AND_STAKE_SHMON: bool
    UNSTAKE_AND_SELL_SHMON: bool

@dataclass
class OrbiterConfig:
    AMOUNT_TO_BRIDGE: Tuple[float, float]
    BRIDGE_ALL: bool
    WAIT_FOR_FUNDS_TO_ARRIVE: bool
    MAX_WAIT_TIME: int


@dataclass
class MadnessConfig:
    SWAP_ALL_TO_MONAD: bool


@dataclass
class DisperseConfig:
    MIN_BALANCE_FOR_DISPERSE: Tuple[float, float]


@dataclass
class LilchogstarsConfig:
    MAX_AMOUNT_FOR_EACH_ACCOUNT: Tuple[int, int]

@dataclass
class MonadkingConfig:
    MAX_AMOUNT_FOR_EACH_ACCOUNT: Tuple[int, int]


@dataclass
class FrontRunnerConfig:
    MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN: Tuple[int, int]
    PAUSE_BETWEEN_TRANSACTIONS: Tuple[int, int]


@dataclass
class MagicEdenConfig:
    NFT_CONTRACTS: List[str]


@dataclass
class MonaiyakuzaConfig:
    MAX_PER_ACCOUNT: Tuple[int, int]


@dataclass
class NarwhalFinanceConfig:
    AMOUNT_USDT_FOR_BET: Tuple[float, float]
    NUMBER_OF_BETS_PER_START: Tuple[int, int]
    PLAY_SLOTS: bool
    PLAY_DICE: bool
    PLAY_COINFLIP: bool

@dataclass
class WithdrawalConfig:
    currency: str
    networks: List[str]
    min_amount: float
    max_amount: float
    wait_for_funds: bool
    max_wait_time: int
    retries: int
    max_balance: float  # Maximum wallet balance to allow withdrawal to


@dataclass
class ExchangesConfig:
    name: str  # Exchange name (OKX, BINANCE, BYBIT)
    apiKey: str
    secretKey: str
    passphrase: str  # Only needed for OKX
    withdrawals: List[WithdrawalConfig]


@dataclass
class OctoSwapConfig:
    SWAP_ALL_TO_MONAD: bool

@dataclass
class FlapshConfig:
    AMOUNT_TO_PAY: Tuple[float, float]
    NUMBER_OF_MEMCOINS_TO_BUY: Tuple[int, int]
    TOKEN_ADDRESS: List[str]

@dataclass
class Config:
    SETTINGS: SettingsConfig
    EXCHANGES: ExchangesConfig
    FAUCET: FaucetConfig
    FLOW: FlowConfig
    APRIORI: AprioriConfig
    MAGMA: MagmaConfig
    KINTSU: KintsuConfig
    GASZIP: GaszipConfig
    SHMONAD: ShmonadConfig
    ORBITER: OrbiterConfig
    OCTO_SWAP: OctoSwapConfig
    DISPERSE: DisperseConfig
    LILCHOGSTARS: LilchogstarsConfig
    MONADKING: MonadkingConfig
    FRONT_RUNNER: FrontRunnerConfig
    MAGICEDEN: MagicEdenConfig
    MEMEBRIDGE: MemebridgeConfig
    CRUSTY_SWAP: CrustySwapConfig
    TESTNET_BRIDGE: TestnetBridgeConfig
    DUSTED: DustedConfig
    NOSTRA: NostraConfig
    MONAIYAKUZA: MonaiyakuzaConfig
    NARWHAL_FINANCE: NarwhalFinanceConfig
    FLAPSH: FlapshConfig
    MADNESS: MadnessConfig
    WALLETS: WalletsConfig = field(default_factory=WalletsConfig)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        """Load configuration from yaml file"""
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # Load tasks from tasks.py
        try:
            # Try to import tasks from tasks.py using a regular import
            import tasks

            if hasattr(tasks, "TASKS"):
                # TASKS now contains preset names
                preset_names = [preset_name.upper() for preset_name in tasks.TASKS]

                # Combine tasks from all specified presets
                combined_tasks = []
                for preset_name in preset_names:
                    if hasattr(tasks, preset_name):
                        preset_tasks = getattr(tasks, preset_name)
                        combined_tasks.extend(preset_tasks)
                    else:
                        print(f"Warning: Preset {preset_name} not found in tasks.py")

                if combined_tasks:
                    tasks_list = combined_tasks
                else:
                    error_msg = "No valid presets found in tasks.py"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
            else:
                error_msg = "No TASKS list found in tasks.py"
                print(f"Error: {error_msg}")
                raise ValueError(error_msg)
        except ImportError as e:
            error_msg = f"Could not import tasks.py: {e}"
            print(f"Error: {error_msg}")
            raise ImportError(error_msg) from e

        return cls(
            SETTINGS=SettingsConfig(
                THREADS=data["SETTINGS"]["THREADS"],
                ATTEMPTS=data["SETTINGS"]["ATTEMPTS"],
                ACCOUNTS_RANGE=tuple(data["SETTINGS"]["ACCOUNTS_RANGE"]),
                EXACT_ACCOUNTS_TO_USE=data["SETTINGS"]["EXACT_ACCOUNTS_TO_USE"],
                PAUSE_BETWEEN_ATTEMPTS=tuple(
                    data["SETTINGS"]["PAUSE_BETWEEN_ATTEMPTS"]
                ),
                PAUSE_BETWEEN_SWAPS=tuple(data["SETTINGS"]["PAUSE_BETWEEN_SWAPS"]),
                RANDOM_PAUSE_BETWEEN_ACCOUNTS=tuple(
                    data["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACCOUNTS"]
                ),
                RANDOM_PAUSE_BETWEEN_ACTIONS=tuple(
                    data["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACTIONS"]
                ),
                RANDOM_INITIALIZATION_PAUSE=tuple(
                    data["SETTINGS"]["RANDOM_INITIALIZATION_PAUSE"]
                ),
                BROWSER_PAUSE_MULTIPLIER=data["SETTINGS"]["BROWSER_PAUSE_MULTIPLIER"],
                TELEGRAM_USERS_IDS=data["SETTINGS"]["TELEGRAM_USERS_IDS"],
                TELEGRAM_BOT_TOKEN=data["SETTINGS"]["TELEGRAM_BOT_TOKEN"],
            ),
            EXCHANGES=ExchangesConfig(
                name=data["EXCHANGES"]["name"],
                apiKey=data["EXCHANGES"]["apiKey"],
                secretKey=data["EXCHANGES"]["secretKey"],
                passphrase=data["EXCHANGES"]["passphrase"],
                withdrawals=[
                    WithdrawalConfig(
                        currency=w["currency"],
                        networks=w["networks"],
                        min_amount=w["min_amount"],
                        max_amount=w["max_amount"],
                        wait_for_funds=w["wait_for_funds"],
                        max_wait_time=w["max_wait_time"],
                        retries=w["retries"],
                        max_balance=w["max_balance"]
                    ) for w in data["EXCHANGES"]["withdrawals"]
                ]
            ),
            FAUCET=FaucetConfig(
                NOCAPTCHA_API_KEY=data["FAUCET"]["NOCAPTCHA_API_KEY"],
                PROXY_FOR_NOCAPTCHA=data["FAUCET"]["PROXY_FOR_NOCAPTCHA"],
                USE_CAPSOLVER_FOR_CLOUDFLARE=data["FAUCET"]["USE_CAPSOLVER_FOR_CLOUDFLARE"],
                CAPSOLVER_API_KEY=data["FAUCET"]["CAPSOLVER_API_KEY"],
                USE_SOLVIUM_FOR_CLOUDFLARE=data["FAUCET"]["USE_SOLVIUM_FOR_CLOUDFLARE"],
                SOLVIUM_API_KEY=data["FAUCET"]["SOLVIUM_API_KEY"],
            ),
            FLOW=FlowConfig(
                TASKS=tasks_list,
                NUMBER_OF_SWAPS=tuple(data["FLOW"]["NUMBER_OF_SWAPS"]),
                PERCENT_OF_BALANCE_TO_SWAP=tuple(
                    data["FLOW"]["PERCENT_OF_BALANCE_TO_SWAP"]
                ),
            ),
            APRIORI=AprioriConfig(
                AMOUNT_TO_STAKE=tuple(data["APRIORI"]["AMOUNT_TO_STAKE"]),
                STAKE=data["APRIORI"]["STAKE"],
                UNSTAKE=data["APRIORI"]["UNSTAKE"],
            ),
            MAGMA=MagmaConfig(
                AMOUNT_TO_STAKE=tuple(data["MAGMA"]["AMOUNT_TO_STAKE"]),
                STAKE=data["MAGMA"]["STAKE"],
                UNSTAKE=data["MAGMA"]["UNSTAKE"],
            ),
            KINTSU=KintsuConfig(
                AMOUNT_TO_STAKE=tuple(data["KINTSU"]["AMOUNT_TO_STAKE"]),
                STAKE=data["KINTSU"]["STAKE"],
                UNSTAKE=data["KINTSU"]["UNSTAKE"],
            ),
            DUSTED=DustedConfig(
                CLAIM=data["DUSTED"]["CLAIM"],
                SKIP_TWITTER_VERIFICATION=data["DUSTED"]["SKIP_TWITTER_VERIFICATION"],
            ),
            NOSTRA=NostraConfig(
                PERCENT_OF_BALANCE_TO_DEPOSIT=tuple(data["NOSTRA"]["PERCENT_OF_BALANCE_TO_DEPOSIT"]),
                DEPOSIT=data["NOSTRA"]["DEPOSIT"],
                BORROW=data["NOSTRA"]["BORROW"],
                REPAY=data["NOSTRA"]["REPAY"],
                WITHDRAW=data["NOSTRA"]["WITHDRAW"],
            ),
            GASZIP=GaszipConfig(
                NETWORKS_TO_REFUEL_FROM=data["GASZIP"]["NETWORKS_TO_REFUEL_FROM"],
                AMOUNT_TO_REFUEL=tuple(data["GASZIP"]["AMOUNT_TO_REFUEL"]),
                MINIMUM_BALANCE_TO_REFUEL=data["GASZIP"]["MINIMUM_BALANCE_TO_REFUEL"],
                WAIT_FOR_FUNDS_TO_ARRIVE=data["GASZIP"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
                MAX_WAIT_TIME=data["GASZIP"]["MAX_WAIT_TIME"],
                BRIDGE_ALL=data["GASZIP"]["BRIDGE_ALL"],
                BRIDGE_ALL_MAX_AMOUNT=data["GASZIP"]["BRIDGE_ALL_MAX_AMOUNT"],
            ),
            MEMEBRIDGE=MemebridgeConfig(
                NETWORKS_TO_REFUEL_FROM=data["MEMEBRIDGE"]["NETWORKS_TO_REFUEL_FROM"],
                AMOUNT_TO_REFUEL=tuple(data["MEMEBRIDGE"]["AMOUNT_TO_REFUEL"]),
                MINIMUM_BALANCE_TO_REFUEL=data["MEMEBRIDGE"][
                    "MINIMUM_BALANCE_TO_REFUEL"
                ],
                WAIT_FOR_FUNDS_TO_ARRIVE=data["MEMEBRIDGE"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
                MAX_WAIT_TIME=data["MEMEBRIDGE"]["MAX_WAIT_TIME"],
                BRIDGE_ALL=data["MEMEBRIDGE"]["BRIDGE_ALL"],
                BRIDGE_ALL_MAX_AMOUNT=data["MEMEBRIDGE"]["BRIDGE_ALL_MAX_AMOUNT"],
            ),
            CRUSTY_SWAP=CrustySwapConfig(
                NETWORKS_TO_REFUEL_FROM=data["CRUSTY_SWAP"]["NETWORKS_TO_REFUEL_FROM"],
                AMOUNT_TO_REFUEL=tuple(data["CRUSTY_SWAP"]["AMOUNT_TO_REFUEL"]),
                MINIMUM_BALANCE_TO_REFUEL=data["CRUSTY_SWAP"]["MINIMUM_BALANCE_TO_REFUEL"],
                WAIT_FOR_FUNDS_TO_ARRIVE=data["CRUSTY_SWAP"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
                MAX_WAIT_TIME=data["CRUSTY_SWAP"]["MAX_WAIT_TIME"],
                BRIDGE_ALL=data["CRUSTY_SWAP"]["BRIDGE_ALL"],
                BRIDGE_ALL_MAX_AMOUNT=data["CRUSTY_SWAP"]["BRIDGE_ALL_MAX_AMOUNT"],
                SELL_PERCENT_OF_BALANCE=tuple(data["CRUSTY_SWAP"]["SELL_PERCENT_OF_BALANCE"]),
                SELL_MAXIMUM_AMOUNT=data["CRUSTY_SWAP"]["SELL_MAXIMUM_AMOUNT"],
            ),
            
            TESTNET_BRIDGE=TestnetBridgeConfig(
                NETWORKS_TO_REFUEL_FROM=data["TESTNET_BRIDGE"][
                    "NETWORKS_TO_REFUEL_FROM"
                ],
                AMOUNT_TO_REFUEL=tuple(data["TESTNET_BRIDGE"]["AMOUNT_TO_REFUEL"]),
                MINIMUM_BALANCE_TO_REFUEL=data["TESTNET_BRIDGE"][
                    "MINIMUM_BALANCE_TO_REFUEL"
                ],
                WAIT_FOR_FUNDS_TO_ARRIVE=data["TESTNET_BRIDGE"][
                    "WAIT_FOR_FUNDS_TO_ARRIVE"
                ],
                MAX_WAIT_TIME=data["TESTNET_BRIDGE"]["MAX_WAIT_TIME"],
                BRIDGE_ALL=data["TESTNET_BRIDGE"]["BRIDGE_ALL"],
                BRIDGE_ALL_MAX_AMOUNT=data["TESTNET_BRIDGE"]["BRIDGE_ALL_MAX_AMOUNT"],
            ),
            SHMONAD=ShmonadConfig(
                PERCENT_OF_BALANCE_TO_SWAP=tuple(
                    data["SHMONAD"]["PERCENT_OF_BALANCE_TO_SWAP"]
                ),
                BUY_AND_STAKE_SHMON=data["SHMONAD"]["BUY_AND_STAKE_SHMON"],
                UNSTAKE_AND_SELL_SHMON=data["SHMONAD"]["UNSTAKE_AND_SELL_SHMON"],
            ),
            ORBITER=OrbiterConfig(
                AMOUNT_TO_BRIDGE=tuple(data["ORBITER"]["AMOUNT_TO_BRIDGE"]),
                BRIDGE_ALL=data["ORBITER"]["BRIDGE_ALL"],
                WAIT_FOR_FUNDS_TO_ARRIVE=data["ORBITER"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
                MAX_WAIT_TIME=data["ORBITER"]["MAX_WAIT_TIME"],
            ),
            DISPERSE=DisperseConfig(
                MIN_BALANCE_FOR_DISPERSE=tuple(
                    data["DISPERSE"]["MIN_BALANCE_FOR_DISPERSE"]
                ),
            ),
            LILCHOGSTARS=LilchogstarsConfig(
                MAX_AMOUNT_FOR_EACH_ACCOUNT=tuple(
                    data["LILCHOGSTARS"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"]
                ),
            ),
            MONADKING=MonadkingConfig(
                MAX_AMOUNT_FOR_EACH_ACCOUNT=tuple(
                    data["MONADKING"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"]
                ),
            ),
            FRONT_RUNNER=FrontRunnerConfig(
                MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN=tuple(
                    data["FRONT_RUNNER"]["MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN"]
                ),
                PAUSE_BETWEEN_TRANSACTIONS=tuple(
                    data["FRONT_RUNNER"]["PAUSE_BETWEEN_TRANSACTIONS"]
                ),
            ),
            MAGICEDEN=MagicEdenConfig(
                NFT_CONTRACTS=data["MAGICEDEN"]["NFT_CONTRACTS"],
            ),
            MONAIYAKUZA=MonaiyakuzaConfig(
                MAX_PER_ACCOUNT=tuple(data["MONAIYAKUZA"]["MAX_PER_ACCOUNT"]),
            ),
            OCTO_SWAP=OctoSwapConfig(
                SWAP_ALL_TO_MONAD=data["OCTO_SWAP"]["SWAP_ALL_TO_MONAD"],
            ),
            NARWHAL_FINANCE=NarwhalFinanceConfig(
                AMOUNT_USDT_FOR_BET=tuple(data["NARWHAL_FINANCE"]["AMOUNT_USDT_FOR_BET"]),
                NUMBER_OF_BETS_PER_START=tuple(data["NARWHAL_FINANCE"]["NUMBER_OF_BETS_PER_START"]),
                PLAY_SLOTS=data["NARWHAL_FINANCE"]["PLAY_SLOTS"],
                PLAY_DICE=data["NARWHAL_FINANCE"]["PLAY_DICE"],
                PLAY_COINFLIP=data["NARWHAL_FINANCE"]["PLAY_COINFLIP"],
            ),
            FLAPSH=FlapshConfig(
                AMOUNT_TO_PAY=tuple(data["FLAPSH"]["AMOUNT_TO_PAY"]),
                NUMBER_OF_MEMCOINS_TO_BUY=tuple(data["FLAPSH"]["NUMBER_OF_MEMCOINS_TO_BUY"]),
                TOKEN_ADDRESS=data["FLAPSH"]["TOKEN_ADDRESS"],
            ),
            MADNESS=MadnessConfig(
                SWAP_ALL_TO_MONAD=data["MADNESS"]["SWAP_ALL_TO_MONAD"],
            ),
        )


# Singleton pattern
def get_config() -> Config:
    """Get configuration singleton"""
    if not hasattr(get_config, "_config"):
        get_config._config = Config.load()
    return get_config._config
