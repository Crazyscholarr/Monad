TASKS = [
    "ALL_TASK",
]

# MAGICEDEN CHỈ HOẠT ĐỘNG VỚI NHỮNG NFT NÀY https://magiceden.io/mint-terminal/monad-testnet

CRUSTY_SWAP = [
    "crusty_refuel",
    # "crusty_sell",
    # "crusty_refuel_from_one_to_all",
]

FAUCET = [
    "faucet",
]

NERZO_SOULBOUND = [
    "nerzo_soulbound",
]

MONAIGG = [
    "monaigg",
]

"""
VI:
Bạn có thể tạo tác vụ của riêng mình với các mô-đun bạn cần 
và thêm nó vào danh sách TASKS hoặc sử dụng các tác vụ mẫu có sẵn của chúng tôi.

( ) - Nghĩa là tất cả các mô-đun trong dấu ngoặc sẽ được thực thi 
theo thứ tự ngẫu nhiên
[ ] - Nghĩa là chỉ một trong các mô-đun trong dấu ngoặc sẽ được thực thi 
theo cách ngẫu nhiên
XEM VÍ DỤ DƯỚI ĐÂY:

--------------------------------
!!! QUAN TRỌNG !!!
VÍ DỤ:

TASKS = [
    "TẠO_TÁC_VỤ_CỦA_BẠN",
]
TẠO_TÁC_VỤ_CỦA_BẠN = [
    "crusty_refuel",
    ("apriori", "magma", "shmonad"),
    ["ambient", "izumi", "bean"],
    "collect_all_to_monad",
]
--------------------------------

DƯỚI ĐÂY LÀ CÁC TÁC VỤ MẪU SẴN CÓ MÀ BẠN CÓ THỂ SỬ DỤNG:
"""

BRIDGE_AND_SWAPS = [
    "crusty_refuel",
    ("izumi", "ambient", "bean", "swaps"),
    "collect_all_to_monad",
]

FULL_TASK = [
    ["izumi", "swaps", "ambient", "bean", "skip"],
    ["izumi", "swaps", "ambient", "bean", "skip", "skip", "skip"],
    ["izumi", "swaps", "ambient", "bean", "skip", "skip", "skip"],
    ["izumi", "lilchogstars", "bean", "swaps", "skip"],
    ["ambient", "izumi", "bean", "skip", "skip"],
    "collect_all_to_monad",
    ["apriori", "magma", "shmonad", "kintsu", "skip", "skip"],
    ["apriori", "magma", "shmonad", "kintsu", "skip"],
    ["ambient", "izumi", "bean", "magiceden", "monadking", "skip"],
    ["magiceden", "monadking", "skip", "skip"],
    "collect_all_to_monad",
    ["ambient", "izumi", "bean", "magiceden", "monadking", "skip"],
    ["izumi", "swaps", "ambient", "bean", "skip", "skip", "skip"],
    ["owlto", "skip", "skip"],
    ["izumi", "swaps", "ambient", "bean", "skip", "skip"],
    "logs",
]

BRIDGE_SEPOLIA_AND_CONVERT_TO_MON = [
    "testnet_bridge",
    "orbiter",
    "collect_all_to_monad",
]

SWAPS_TASK = [
    ("izumi", "ambient", "bean", "swaps"),
    "collect_all_to_monad",
]

STAKING_TASK = [
    ("apriori", "magma", "shmonad", "kintsu"),
]

EXCHANGE_TASK = [
    "cex_withdrawal",
]

EXCHANGE_AND_TESTNET_BRIDGE_TASK = [
    "cex_withdrawal",
    "testnet_bridge",
    "orbiter",
    "collect_all_to_monad",
]

EXCHANGE_AND_CRUSTY_SWAP_TASK = [
    "cex_withdrawal",
    "crusty_refuel",
]

EXCHANGE_AND_MEMEBRIDGE_TASK = [
    "cex_withdrawal",
    "memebridge",
]
ALL_TASK = [
    *SWAPS_TASK,
    *STAKING_TASK,
    *EXCHANGE_TASK,
    *EXCHANGE_AND_TESTNET_BRIDGE_TASK,
    *EXCHANGE_AND_CRUSTY_SWAP_TASK,
    *EXCHANGE_AND_MEMEBRIDGE_TASK,
    *BRIDGE_AND_SWAPS,
    *BRIDGE_SEPOLIA_AND_CONVERT_TO_MON,
    *CRUSTY_SWAP,
    *FAUCET,
    *NERZO_SOULBOUND,
    *MONAIGG,
    *FULL_TASK,
]

# Thêm ALL_TASK vào danh sách TASKS nếu cần

# FAUCETS
# "disperse_farm_accounts" - phân phối token từ tài khoản farm sang tài khoản chính | keys_for_faucet.txt -> private_keys.txt
# "disperse_from_one_wallet" - phân phối token từ một ví sang tất cả các ví khác | keys_for_faucet.txt (ví đầu tiên) -> private_keys.txt

# SWAPS
# "collect_all_to_monad" - hoán đổi tất cả token sang token gốc (MON)
# "swaps" - hoán đổi token trên trang testnet.monad.xyz/
# "bean" - hoán đổi token trên Bean DEX
# "ambient" - hoán đổi token trên Ambient DEX
# "izumi" - hoán đổi token trên Izumi DEX
# "madness_swaps" - hoán đổi token trên madness.finance/swap

# STAKES
# "apriori" - stake token MON
# "magma" - stake token MON trên Magma
# "shmonad" - mua và stake shmon trên shmonad.xyz | XEM CÀI ĐẶT DƯỚI
# "kintsu" - stake token MON trên kintsu.xyz/
# "nostra" - nạp, vay, trả, rút
# "multiplifi" - stake token USDC trên https://testnet.multipli.fi/?stake-tab=stake
# "flapsh" - mua memcoin bằng MON trên https://monad.flap.sh/board

# MINT
# "magiceden" - mint NFT trên magiceden.io
# "owlto" - triển khai hợp đồng trên Owlto
# "lilchogstars" - mint NFT trên testnet.lilchogstars.com/
# "monadking" - mint NFT trên nerzo.xyz/monadking
# "monadking_unlocked" - mint NFT trên www.nerzo.xyz/unlocked
# "easynode_deploy" - triển khai hợp đồng trên easynode.xyz
# "onchaingm_deploy" - triển khai hợp đồng trên onchaingm.com/deploy
# "morkie_monhog" - mint NFT trên https://morkie.xyz/monhog # giá 0.5 MON
# "morkie_monarch" - mint NFT trên https://morkie.xyz/monarch # giá 0.1 MON
# "monaigg" - mint NFT trên https://monai.gg/nft
# "nerzo_soulbound" - mint NFT trên https://nerzo.xyz/soulbound

# REFUEL
# "crusty_refuel" - nạp từ arbitrum, optimism, base sang monad
# "gaszip" - nạp gaszip từ arbitrum, optimism, base sang monad
# "orbiter" - bridge ETH từ Sepolia sang Monad qua Orbiter
# "memebridge" - nạp memebridge từ arbitrum, optimism, base sang monad

# RÚT TIỀN TỪ SÀN GIAO DỊCH
# "cex_withdrawal" - rút token từ sàn giao dịch

# TRÒ CHƠI
# "frontrunner" - chơi trò chơi frontrunner

# KHÁC
# "logs" - hiển thị nhật ký: số dư MON | số giao dịch | số dư trung bình | số giao dịch trung bình
# "nad_domains" - đăng ký tên miền ngẫu nhiên trên nad.domains
# "narwhal_finance" - chơi trò chơi trên testnet.narwhal.finance/carnival
# "monsternad_whitelist" - thêm vào danh sách trắng monsternad airdrop.monsternad.xyz/dashboard/