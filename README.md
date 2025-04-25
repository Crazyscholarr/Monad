# Tự động hóa Monad Testnet

Công cụ này tự động hóa các tương tác với Monad testnet, bao gồm nhiều hoạt động DeFi và tương tác với token.



# Tất cả các tính năng đều có sẵn trong cấu hình:
"crusty_refuel" - mua MON testnet từ cầu nối này https://www.crustyswap.com/

# FAUCETS
"faucet" - nhận token từ faucet

"farm_faucet" - nhận token từ faucet trên TÀI KHOẢN FARM (data/keys_for_faucet.txt)

"disperse_farm_accounts" - phân phối token từ tài khoản farm sang tài khoản chính | keys_for_faucet.txt -> private_keys.txt

"disperse_from_one_wallet" - phân phối token từ một ví sang tất cả các ví khác | keys_for_faucet.txt (ví đầu tiên) -> private_keys.txt

# SWAPS
"collect_all_to_monad" - hoán đổi tất cả token sang token gốc (MON)

"swaps" - hoán đổi token trên trang testnet.monad.xyz/

"bean" - hoán đổi token trên Bean DEX

"ambient" - hoán đổi token trên Ambient DEX

"izumi" - hoán đổi token trên Izumi DEX

# STAKES
"apriori" - stake token MON

"magma" - stake token MON trên Magma

"shmonad" - mua và stake shmon trên shmonad.xyz | XEM CÀI ĐẶT DƯỚI

"kintsu" - stake token MON trên kintsu.xyz/

# MINT
"magiceden" - mint NFT trên magiceden.io

"owlto" - triển khai hợp đồng trên Owlto

"lilchogstars" - mint NFT trên testnet.lilchogstars.com/

"monadking" - mint NFT trên nerzo.xyz/monadking

"monadking_unlocked" - mint NFT trên www.nerzo.xyz/unlocked

# REFUEL
"gaszip" - nạp gaszip từ arbitrum, optimism, base sang monad

"orbiter" - bridge ETH từ Sepolia sang Monad qua Orbiter

"memebridge" - nạp memebridge từ arbitrum, optimism, base sang monad

# KHÁC
"logs" - hiển thị nhật ký: số dư MON | số giao dịch | số dư trung bình | số giao dịch trung bình

"nad_domains" - đăng ký tên miền ngẫu nhiên trên nad.domains

"aircraft" - mint NFT trên aircraft.fun

## Yêu cầu
- Python 3.11 hoặc cao hơn

## Cài đặt

1. Sao chép kho lưu trữ
```bash
git clone 
cd MONAD_2.0
```
2. Cài đặt các thư viện phụ thuộc
```bash

pip install -r requirements.txt
```
3. Cấu hình bot bằng cách khởi động nó (py main.py) và chọn tùy chọn chỉnh sửa cấu hình
4. Thêm dữ liệu của bạn vào các file sau:
    ```data/private_keys.txt ```- Một khóa riêng trên mỗi dòng
    ```data/proxies.txt ```- Một proxy trên mỗi dòng (định dạng: user:pass@ip:port)
### Chạy bot
```bash
python main.py

```


---
# Monad
