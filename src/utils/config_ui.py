import customtkinter as ctk
import yaml
import os


class ConfigUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Define color scheme
        self.colors = {
            "bg": "#121212",  # Slightly lighter black background
            "frame_bg": "#1e1e1e",  # Slightly lighter frame background
            "accent": "#B8860B",  # More muted gold/yellow (DarkGoldenrod)
            "text": "#ffffff",  # White text
            "entry_bg": "#1e1e1e",  # Dark input background
            "hover": "#8B6914",  # Darker muted yellow for hover
        }

        # Standardize input widths
        self.input_sizes = {
            "tiny": 70,  # For small numbers (1-2 digits)
            "small": 115,  # For short text/numbers
            "medium": 180,  # For medium length text
            "large": 250,  # For long text
            "extra_large": 350,  # For very long text/lists
        }

        self.root = ctk.CTk()
        self.root.title("StarLabs Monad Configuration")
        self.root.geometry("1250x800")
        self.root.minsize(1250, 800)  # Set minimum window size
        self.root.configure(fg_color=self.colors["bg"])

        # Create header frame
        header_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg"])
        header_frame.pack(
            fill="x", padx=50, pady=(20, 0)
        )  # Increased left/right padding

        # Header on the left
        header = ctk.CTkLabel(
            header_frame,
            text="🌟 StarLabs Monad Configuration",
            font=("Helvetica", 24, "bold"),
            text_color=self.colors["accent"],
            anchor="w",
        )
        header.pack(side="left", padx=5)  # Added left padding

        # Save button in the top right
        self.save_button = ctk.CTkButton(
            header_frame,
            text="⚡ SAVE",  # Changed icon and made text uppercase
            command=self._save_and_close,
            font=("Helvetica", 18, "bold"),  # Increased font size
            height=45,
            width=160,  # Slightly wider
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"],
            corner_radius=10,
        )
        self.save_button.pack(side="right", padx=5)  # Added right padding

        # Create main frame with scrollbar
        self.main_frame = ctk.CTkFrame(self.root, fg_color=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=5)

        # Add canvas and scrollbar
        self.canvas = ctk.CTkCanvas(
            self.main_frame, bg=self.colors["bg"], highlightthickness=0
        )
        self.scrollbar = ctk.CTkScrollbar(
            self.main_frame,
            orientation="vertical",
            command=self.canvas.yview,
            fg_color=self.colors["frame_bg"],
            button_color=self.colors["accent"],
            button_hover_color=self.colors["hover"],
        )
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color=self.colors["bg"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # Pack scrollbar components
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Create window in canvas with proper width
        self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            width=self.canvas.winfo_width(),  # Use canvas width
        )

        # Update canvas width when window is resized
        def update_canvas_width(event):
            self.canvas.itemconfig(
                self.canvas.find_withtag("all")[0], width=event.width
            )

        self.canvas.bind("<Configure>", update_canvas_width)

        # Configure scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.load_config()
        self.create_widgets()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)

        # Проверяем наличие всех необходимых секций
        if "NARWHAL_FINANCE" not in self.config:
            self.config["NARWHAL_FINANCE"] = {
                "AMOUNT_USDT_FOR_BET": [5, 50],
                "NUMBER_OF_BETS_PER_START": [1, 3],
                "PLAY_SLOTS": True,
                "PLAY_DICE": True,
                "PLAY_COINFLIP": True,
            }

        if "MONAIYAKUZA" not in self.config:
            self.config["MONAIYAKUZA"] = {"MAX_PER_ACCOUNT": [1, 1]}

        if "OCTO_SWAP" not in self.config:
            self.config["OCTO_SWAP"] = {"SWAP_ALL_TO_MONAD": False}

    def create_range_inputs(self, parent, label, config_value, width=120):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(1, weight=1)  # Column for inputs will expand

        ctk.CTkLabel(
            frame,
            text=f"{label}:",
            width=200,
            anchor="w",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        ).grid(row=0, column=0, padx=(10, 10), sticky="w")

        input_frame = ctk.CTkFrame(frame, fg_color=self.colors["frame_bg"])
        input_frame.grid(row=0, column=1, sticky="e", padx=(0, 10))

        min_entry = ctk.CTkEntry(
            input_frame,
            width=width,
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["entry_bg"],
            text_color=self.colors["text"],
            border_color=self.colors["accent"],
        )
        min_entry.pack(side="left", padx=(0, 5))
        min_entry.insert(0, str(config_value[0]))

        ctk.CTkLabel(
            input_frame,
            text=" - ",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        ).pack(side="left", padx=5)

        max_entry = ctk.CTkEntry(
            input_frame,
            width=width,
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["entry_bg"],
            text_color=self.colors["text"],
            border_color=self.colors["accent"],
        )
        max_entry.pack(side="left", padx=(5, 0))
        max_entry.insert(0, str(config_value[1]))

        return min_entry, max_entry

    def create_single_input(self, parent, label, config_value, width=300):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(1, weight=1)  # Column for input will expand

        ctk.CTkLabel(
            frame,
            text=f"{label}:",
            width=200,
            anchor="w",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        ).grid(row=0, column=0, padx=(10, 10), sticky="w")

        entry = ctk.CTkEntry(
            frame,
            width=width,
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["entry_bg"],
            text_color=self.colors["text"],
            border_color=self.colors["accent"],
        )
        entry.grid(row=0, column=1, padx=(0, 10), sticky="e")
        entry.insert(0, str(config_value))

        return entry

    def create_checkbox(self, parent, label, config_value):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(0, weight=1)

        var = ctk.BooleanVar(value=config_value)
        checkbox = ctk.CTkCheckBox(
            frame,
            text=label,
            variable=var,
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            border_color=self.colors["accent"],
        )
        checkbox.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        return var

    def create_section(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", padx=5, pady=5)

        label = ctk.CTkLabel(
            frame,
            text=title,
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["accent"],
        )
        label.pack(anchor="w", padx=10, pady=10)

        return frame

    def create_category_header(self, parent, title):
        header = ctk.CTkLabel(
            parent,
            text=title,
            font=("Helvetica", 18, "bold"),
            text_color=self.colors["accent"],
        )
        header.pack(fill="x", pady=(20, 10), padx=5)

    def create_network_checkboxes(
        self, parent, label, config_value, available_networks=None
    ):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", pady=5)

        label = ctk.CTkLabel(
            frame,
            text=f"{label}:",
            width=200,
            anchor="w",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        )
        label.pack(anchor="w", padx=10, pady=(5, 0))

        networks_frame = ctk.CTkFrame(frame, fg_color=self.colors["frame_bg"])
        networks_frame.pack(fill="x", padx=10, pady=5)

        # Use provided networks or default to the standard three
        networks = available_networks or ["Arbitrum", "Base", "Optimism"]
        checkboxes = []

        for network in networks:
            var = ctk.BooleanVar(value=network in config_value)
            checkbox = ctk.CTkCheckBox(
                networks_frame,
                text=network,
                variable=var,
                font=("Helvetica", 12, "bold"),
                text_color=self.colors["text"],
                fg_color=self.colors["accent"],
                hover_color=self.colors["hover"],
                border_color=self.colors["accent"],
            )
            checkbox.pack(side="left", padx=10, pady=5)
            checkboxes.append((network, var))

        return checkboxes

    def create_nft_contracts_list(self, parent, label, config_value):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["frame_bg"])
        frame.pack(fill="x", pady=5)

        label = ctk.CTkLabel(
            frame,
            text=f"{label}:",
            width=200,
            anchor="w",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        )
        label.pack(anchor="w", padx=10, pady=(5, 0))

        # Создаем фрейм для списка контрактов
        contracts_frame = ctk.CTkFrame(frame, fg_color=self.colors["frame_bg"])
        contracts_frame.pack(fill="x", padx=10, pady=5)

        # Создаем Listbox для отображения контрактов
        contracts_list = ctk.CTkTextbox(
            contracts_frame,
            height=100,
            width=self.input_sizes["extra_large"],
            font=("Helvetica", 12),
            text_color=self.colors["text"],
            fg_color=self.colors["entry_bg"],
            border_color=self.colors["accent"],
        )
        contracts_list.pack(side="left", padx=(0, 10), fill="both", expand=True)

        # Добавляем существующие контракты
        contracts_list.insert("1.0", "\n".join(config_value))

        # Создаем фрейм для кнопок управления
        buttons_frame = ctk.CTkFrame(contracts_frame, fg_color=self.colors["frame_bg"])
        buttons_frame.pack(side="left", fill="y")

        # Поле для ввода нового контракта
        new_contract_entry = ctk.CTkEntry(
            buttons_frame,
            width=200,
            font=("Helvetica", 12),
            placeholder_text="Enter new contract address",
            fg_color=self.colors["entry_bg"],
            text_color=self.colors["text"],
            border_color=self.colors["accent"],
        )
        new_contract_entry.pack(pady=(0, 5))

        def add_contract():
            new_contract = new_contract_entry.get().strip()
            if new_contract:
                current_text = contracts_list.get("1.0", "end-1c")
                if current_text:
                    contracts_list.insert("end", f"\n{new_contract}")
                else:
                    contracts_list.insert("1.0", new_contract)
                new_contract_entry.delete(0, "end")

        def remove_selected():
            try:
                selection = contracts_list.tag_ranges("sel")
                if selection:
                    contracts_list.delete(selection[0], selection[1])
            except:
                pass

        # Кнопки управления
        add_button = ctk.CTkButton(
            buttons_frame,
            text="Add Contract",
            command=add_contract,
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"],
            width=120,
        )
        add_button.pack(pady=5)

        remove_button = ctk.CTkButton(
            buttons_frame,
            text="Remove Selected",
            command=remove_selected,
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            text_color=self.colors["text"],
            width=120,
        )
        remove_button.pack(pady=5)

        return contracts_list

    def create_widgets(self):
        # Create two columns using pack
        columns_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=self.colors["bg"])
        columns_frame.pack(fill="both", expand=True)

        left_column = ctk.CTkFrame(columns_frame, fg_color=self.colors["bg"])
        left_column.pack(side="left", fill="both", expand=True, padx=5)

        right_column = ctk.CTkFrame(columns_frame, fg_color=self.colors["bg"])
        right_column.pack(side="left", fill="both", expand=True, padx=5)

        # LEFT COLUMN

        # General Settings Category
        self.create_category_header(left_column, "⚙️ GENERAL SETTINGS")
        settings = self.create_section(left_column, "SETTINGS")
        self.threads_entry = self.create_single_input(
            settings,
            "THREADS",
            self.config["SETTINGS"]["THREADS"],
            width=self.input_sizes["tiny"],
        )
        self.attempts_entry = self.create_single_input(
            settings,
            "ATTEMPTS",
            self.config["SETTINGS"]["ATTEMPTS"],
            width=self.input_sizes["tiny"],
        )
        self.acc_range_start, self.acc_range_end = self.create_range_inputs(
            settings,
            "ACCOUNTS_RANGE",
            self.config["SETTINGS"]["ACCOUNTS_RANGE"],
            width=self.input_sizes["tiny"],
        )

        # Add EXACT_ACCOUNTS_TO_USE
        self.exact_accounts = self.create_single_input(
            settings,
            "EXACT_ACCOUNTS_TO_USE",
            ", ".join(map(str, self.config["SETTINGS"]["EXACT_ACCOUNTS_TO_USE"])),
            width=self.input_sizes["large"],
        )

        self.pause_attempts_min, self.pause_attempts_max = self.create_range_inputs(
            settings,
            "PAUSE_BETWEEN_ATTEMPTS",
            self.config["SETTINGS"]["PAUSE_BETWEEN_ATTEMPTS"],
            width=self.input_sizes["small"],
        )
        self.pause_swaps_min, self.pause_swaps_max = self.create_range_inputs(
            settings,
            "PAUSE_BETWEEN_SWAPS",
            self.config["SETTINGS"]["PAUSE_BETWEEN_SWAPS"],
            width=self.input_sizes["small"],
        )
        self.pause_accounts_min, self.pause_accounts_max = self.create_range_inputs(
            settings,
            "RANDOM_PAUSE_BETWEEN_ACCOUNTS",
            self.config["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACCOUNTS"],
            width=self.input_sizes["small"],
        )
        self.pause_actions_min, self.pause_actions_max = self.create_range_inputs(
            settings,
            "RANDOM_PAUSE_BETWEEN_ACTIONS",
            self.config["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACTIONS"],
            width=self.input_sizes["small"],
        )
        self.init_pause_min, self.init_pause_max = self.create_range_inputs(
            settings,
            "RANDOM_INITIALIZATION_PAUSE",
            self.config["SETTINGS"]["RANDOM_INITIALIZATION_PAUSE"],
            width=self.input_sizes["small"],
        )
        self.browser_multiplier = self.create_single_input(
            settings,
            "BROWSER_PAUSE_MULTIPLIER",
            self.config["SETTINGS"]["BROWSER_PAUSE_MULTIPLIER"],
            width=self.input_sizes["tiny"],
        )

        # Add Telegram settings
        self.telegram_ids = self.create_single_input(
            settings,
            "TELEGRAM_USERS_IDS",
            ", ".join(map(str, self.config["SETTINGS"]["TELEGRAM_USERS_IDS"])),
            width=self.input_sizes["large"],
        )
        self.telegram_token = self.create_single_input(
            settings,
            "TELEGRAM_BOT_TOKEN",
            self.config["SETTINGS"]["TELEGRAM_BOT_TOKEN"],
            width=self.input_sizes["extra_large"],
        )

        # FAUCET Category
        self.create_category_header(left_column, "🚰 FAUCETS")

        faucet = self.create_section(left_column, "FAUCET")
        self.nocaptcha_key = self.create_single_input(
            faucet, "NOCAPTCHA_API_KEY", self.config["FAUCET"]["NOCAPTCHA_API_KEY"]
        )
        self.proxy_nocaptcha = self.create_single_input(
            faucet, "PROXY_FOR_NOCAPTCHA", self.config["FAUCET"]["PROXY_FOR_NOCAPTCHA"]
        )
        # Add new Cloudflare settings
        self.use_capsolver = self.create_checkbox(
            faucet,
            "USE_CAPSOLVER_FOR_CLOUDFLARE",
            self.config["FAUCET"]["USE_CAPSOLVER_FOR_CLOUDFLARE"],
        )
        self.capsolver_key = self.create_single_input(
            faucet, "CAPSOLVER_API_KEY", self.config["FAUCET"]["CAPSOLVER_API_KEY"]
        )

        disperse = self.create_section(left_column, "DISPERSE")
        self.min_balance_min, self.min_balance_max = self.create_range_inputs(
            disperse,
            "MIN_BALANCE_FOR_DISPERSE",
            self.config["DISPERSE"]["MIN_BALANCE_FOR_DISPERSE"],
        )

        # DUSTED Category
        dusted = self.create_section(left_column, "DUSTED")
        self.dusted_claim = self.create_checkbox(
            dusted,
            "CLAIM",
            self.config["DUSTED"]["CLAIM"],
        )

        # Add the SKIP_TWITTER_VERIFICATION checkbox after the CLAIM checkbox
        self.dusted_skip_twitter_verification = self.create_checkbox(
            dusted,
            "SKIP_TWITTER_VERIFICATION",
            self.config["DUSTED"]["SKIP_TWITTER_VERIFICATION"],
        )

        # Swaps Category
        self.create_category_header(left_column, "💱 SWAPS")

        flow = self.create_section(left_column, "FLOW")
        self.swaps_min, self.swaps_max = self.create_range_inputs(
            flow, "NUMBER_OF_SWAPS", self.config["FLOW"]["NUMBER_OF_SWAPS"]
        )
        self.balance_swap_min, self.balance_swap_max = self.create_range_inputs(
            flow,
            "PERCENT_OF_BALANCE_TO_SWAP",
            self.config["FLOW"]["PERCENT_OF_BALANCE_TO_SWAP"],
        )

        # NFT Category
        self.create_category_header(left_column, "🎨 NFT")

        # Add LILCHOGSTARS section
        lilchog = self.create_section(left_column, "LILCHOGSTARS")
        self.lilchog_amount_min, self.lilchog_amount_max = self.create_range_inputs(
            lilchog,
            "MAX_AMOUNT_FOR_EACH_ACCOUNT",
            self.config["LILCHOGSTARS"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"],
        )

        # Add MONADKING section
        monadking = self.create_section(left_column, "MONADKING")
        self.monadking_amount_min, self.monadking_amount_max = self.create_range_inputs(
            monadking,
            "MAX_AMOUNT_FOR_EACH_ACCOUNT",
            self.config["MONADKING"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"],
        )

        # Add MAGICEDEN section
        magiceden = self.create_section(left_column, "MAGICEDEN")
        self.magiceden_contracts = self.create_nft_contracts_list(
            magiceden,
            "NFT_CONTRACTS",
            self.config["MAGICEDEN"]["NFT_CONTRACTS"],
        )

        # FRONT_RUNNER
        frame_front_runner = self.create_section(right_column, "FRONT_RUNNER")

        self.max_transactions_for_one_run = self.create_range_inputs(
            frame_front_runner,
            "MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN:",
            self.config["FRONT_RUNNER"]["MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN"],
        )

        self.pause_between_transactions = self.create_range_inputs(
            frame_front_runner,
            "PAUSE_BETWEEN_TRANSACTIONS:",
            self.config["FRONT_RUNNER"]["PAUSE_BETWEEN_TRANSACTIONS"],
        )

        # RIGHT COLUMN

        # Staking Category
        self.create_category_header(right_column, "🥩 STAKING")

        apriori = self.create_section(right_column, "APRIORI")
        self.apriori_stake_min, self.apriori_stake_max = self.create_range_inputs(
            apriori, "AMOUNT_TO_STAKE", self.config["APRIORI"]["AMOUNT_TO_STAKE"]
        )
        self.apriori_stake = self.create_checkbox(
            apriori,
            "STAKE",
            self.config["APRIORI"]["STAKE"],
        )
        self.apriori_unstake = self.create_checkbox(
            apriori,
            "UNSTAKE",
            self.config["APRIORI"]["UNSTAKE"],
        )

        magma = self.create_section(right_column, "MAGMA")
        self.magma_stake_min, self.magma_stake_max = self.create_range_inputs(
            magma, "AMOUNT_TO_STAKE", self.config["MAGMA"]["AMOUNT_TO_STAKE"]
        )
        self.magma_stake = self.create_checkbox(
            magma,
            "STAKE",
            self.config["MAGMA"]["STAKE"],
        )
        self.magma_unstake = self.create_checkbox(
            magma,
            "UNSTAKE",
            self.config["MAGMA"]["UNSTAKE"],
        )

        kintsu = self.create_section(right_column, "KINTSU")
        self.kintsu_stake_min, self.kintsu_stake_max = self.create_range_inputs(
            kintsu, "AMOUNT_TO_STAKE", self.config["KINTSU"]["AMOUNT_TO_STAKE"]
        )
        self.kintsu_stake = self.create_checkbox(
            kintsu,
            "STAKE",
            self.config["KINTSU"]["STAKE"],
        )
        self.kintsu_unstake = self.create_checkbox(
            kintsu,
            "UNSTAKE",
            self.config["KINTSU"]["UNSTAKE"],
        )

        shmonad = self.create_section(right_column, "SHMONAD")
        self.buy_stake = self.create_checkbox(
            shmonad,
            "BUY_AND_STAKE_SHMON",
            self.config["SHMONAD"]["BUY_AND_STAKE_SHMON"],
        )
        self.unstake_sell = self.create_checkbox(
            shmonad,
            "UNSTAKE_AND_SELL_SHMON",
            self.config["SHMONAD"]["UNSTAKE_AND_SELL_SHMON"],
        )
        self.shmonad_percent_min, self.shmonad_percent_max = self.create_range_inputs(
            shmonad,
            "PERCENT_OF_BALANCE_TO_SWAP",
            self.config["SHMONAD"]["PERCENT_OF_BALANCE_TO_SWAP"],
        )

        # Bridge & Refuel Category
        self.create_category_header(right_column, "🌉 BRIDGE & REFUEL")

        # Add CRUSTY_SWAP section as the first item
        crusty_swap = self.create_section(right_column, "CRUSTY_SWAP")
        self.crusty_swap_networks = self.create_network_checkboxes(
            crusty_swap,
            "NETWORKS_TO_REFUEL_FROM",
            self.config["CRUSTY_SWAP"]["NETWORKS_TO_REFUEL_FROM"],
            # available_networks=["Arbitrum", "Base", "Optimism", "ZkSync"]
            available_networks=["Arbitrum", "Base", "Optimism"],
        )
        self.crusty_swap_amount_min, self.crusty_swap_amount_max = (
            self.create_range_inputs(
                crusty_swap,
                "AMOUNT_TO_REFUEL",
                self.config["CRUSTY_SWAP"]["AMOUNT_TO_REFUEL"],
            )
        )
        self.crusty_swap_min_balance = self.create_single_input(
            crusty_swap,
            "MINIMUM_BALANCE_TO_REFUEL",
            self.config["CRUSTY_SWAP"]["MINIMUM_BALANCE_TO_REFUEL"],
            width=self.input_sizes["tiny"],
        )
        self.crusty_swap_wait = self.create_checkbox(
            crusty_swap,
            "WAIT_FOR_FUNDS_TO_ARRIVE",
            self.config["CRUSTY_SWAP"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
        )
        self.crusty_swap_wait_time = self.create_single_input(
            crusty_swap,
            "MAX_WAIT_TIME",
            self.config["CRUSTY_SWAP"]["MAX_WAIT_TIME"],
            width=self.input_sizes["tiny"],
        )
        self.crusty_swap_bridge_all = self.create_checkbox(
            crusty_swap,
            "BRIDGE_ALL (bridge maximum available balance)",
            self.config["CRUSTY_SWAP"]["BRIDGE_ALL"],
        )
        self.crusty_swap_bridge_max = self.create_single_input(
            crusty_swap,
            "BRIDGE_ALL_MAX_AMOUNT (max to bridge with 1-3% random reduction)",
            self.config["CRUSTY_SWAP"]["BRIDGE_ALL_MAX_AMOUNT"],
            width=self.input_sizes["small"],
        )
        # Add CRUSTY_SWAP specific fields
        self.crusty_swap_sell_min, self.crusty_swap_sell_max = self.create_range_inputs(
            crusty_swap,
            "SELL_PERCENT_OF_BALANCE",
            self.config["CRUSTY_SWAP"]["SELL_PERCENT_OF_BALANCE"],
        )
        self.crusty_swap_sell_max_amount = self.create_single_input(
            crusty_swap,
            "SELL_MAXIMUM_AMOUNT",
            self.config["CRUSTY_SWAP"]["SELL_MAXIMUM_AMOUNT"],
            width=self.input_sizes["small"],
        )

        # Add GASZIP section
        gaszip = self.create_section(right_column, "GASZIP")
        self.gaszip_networks = self.create_network_checkboxes(
            gaszip,
            "NETWORKS_TO_REFUEL_FROM",
            self.config["GASZIP"]["NETWORKS_TO_REFUEL_FROM"],
        )
        self.gaszip_amount_min, self.gaszip_amount_max = self.create_range_inputs(
            gaszip, "AMOUNT_TO_REFUEL", self.config["GASZIP"]["AMOUNT_TO_REFUEL"]
        )
        self.gaszip_min_balance = self.create_single_input(
            gaszip,
            "MINIMUM_BALANCE_TO_REFUEL",
            self.config["GASZIP"]["MINIMUM_BALANCE_TO_REFUEL"],
            width=self.input_sizes["tiny"],
        )
        self.gaszip_wait = self.create_checkbox(
            gaszip,
            "WAIT_FOR_FUNDS_TO_ARRIVE",
            self.config["GASZIP"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
        )
        self.gaszip_wait_time = self.create_single_input(
            gaszip,
            "MAX_WAIT_TIME",
            self.config["GASZIP"]["MAX_WAIT_TIME"],
            width=self.input_sizes["tiny"],
        )
        self.gaszip_bridge_all = self.create_checkbox(
            gaszip,
            "BRIDGE_ALL (bridge maximum available balance)",
            self.config["GASZIP"].get("BRIDGE_ALL"),
        )
        self.gaszip_bridge_max = self.create_single_input(
            gaszip,
            "BRIDGE_ALL_MAX_AMOUNT (max to bridge with 1-3% random reduction)",
            self.config["GASZIP"].get("BRIDGE_ALL_MAX_AMOUNT"),
            width=self.input_sizes["small"],
        )

        # Add MEMEBRIDGE section
        memebridge = self.create_section(right_column, "MEMEBRIDGE")
        self.memebridge_networks = self.create_network_checkboxes(
            memebridge,
            "NETWORKS_TO_REFUEL_FROM",
            self.config["MEMEBRIDGE"]["NETWORKS_TO_REFUEL_FROM"],
        )
        self.memebridge_amount_min, self.memebridge_amount_max = (
            self.create_range_inputs(
                memebridge,
                "AMOUNT_TO_REFUEL",
                self.config["MEMEBRIDGE"]["AMOUNT_TO_REFUEL"],
            )
        )
        self.memebridge_min_balance = self.create_single_input(
            memebridge,
            "MINIMUM_BALANCE_TO_REFUEL",
            self.config["MEMEBRIDGE"]["MINIMUM_BALANCE_TO_REFUEL"],
            width=self.input_sizes["tiny"],
        )
        self.memebridge_wait = self.create_checkbox(
            memebridge,
            "WAIT_FOR_FUNDS_TO_ARRIVE",
            self.config["MEMEBRIDGE"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
        )
        self.memebridge_wait_time = self.create_single_input(
            memebridge,
            "MAX_WAIT_TIME",
            self.config["MEMEBRIDGE"]["MAX_WAIT_TIME"],
            width=self.input_sizes["tiny"],
        )
        self.memebridge_bridge_all = self.create_checkbox(
            memebridge,
            "BRIDGE_ALL (bridge maximum available balance)",
            self.config["MEMEBRIDGE"].get("BRIDGE_ALL"),
        )
        self.memebridge_bridge_max = self.create_single_input(
            memebridge,
            "BRIDGE_ALL_MAX_AMOUNT (max to bridge with 1-3% random reduction)",
            self.config["MEMEBRIDGE"].get("BRIDGE_ALL_MAX_AMOUNT"),
            width=self.input_sizes["small"],
        )

        # Add TESTNET_BRIDGE section
        testnet = self.create_section(right_column, "TESTNET_BRIDGE")
        self.testnet_networks = self.create_network_checkboxes(
            testnet,
            "NETWORKS_TO_REFUEL_FROM",
            self.config["TESTNET_BRIDGE"]["NETWORKS_TO_REFUEL_FROM"],
            available_networks=["Arbitrum", "Optimism"],
        )
        self.testnet_amount_min, self.testnet_amount_max = self.create_range_inputs(
            testnet,
            "AMOUNT_TO_REFUEL",
            self.config["TESTNET_BRIDGE"]["AMOUNT_TO_REFUEL"],
        )
        self.testnet_min_balance = self.create_single_input(
            testnet,
            "MINIMUM_BALANCE_TO_REFUEL",
            self.config["TESTNET_BRIDGE"]["MINIMUM_BALANCE_TO_REFUEL"],
            width=self.input_sizes["tiny"],
        )
        self.testnet_wait = self.create_checkbox(
            testnet,
            "WAIT_FOR_FUNDS_TO_ARRIVE",
            self.config["TESTNET_BRIDGE"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
        )
        self.testnet_wait_time = self.create_single_input(
            testnet,
            "MAX_WAIT_TIME",
            self.config["TESTNET_BRIDGE"]["MAX_WAIT_TIME"],
            width=self.input_sizes["tiny"],
        )

        # Add the BRIDGE_ALL checkbox
        self.testnet_bridge_all = self.create_checkbox(
            testnet,
            "BRIDGE_ALL",
            self.config["TESTNET_BRIDGE"]["BRIDGE_ALL"],
        )

        # Add the BRIDGE_ALL_MAX_AMOUNT input
        self.testnet_bridge_max = self.create_single_input(
            testnet,
            "BRIDGE_ALL_MAX_AMOUNT",
            self.config["TESTNET_BRIDGE"]["BRIDGE_ALL_MAX_AMOUNT"],
            width=100,
        )

        orbiter = self.create_section(right_column, "ORBITER")
        self.orbiter_amount_min, self.orbiter_amount_max = self.create_range_inputs(
            orbiter, "AMOUNT_TO_BRIDGE", self.config["ORBITER"]["AMOUNT_TO_BRIDGE"]
        )
        self.bridge_all = self.create_checkbox(
            orbiter, "BRIDGE_ALL", self.config["ORBITER"]["BRIDGE_ALL"]
        )
        self.orbiter_wait = self.create_checkbox(
            orbiter,
            "WAIT_FOR_FUNDS_TO_ARRIVE",
            self.config["ORBITER"]["WAIT_FOR_FUNDS_TO_ARRIVE"],
        )
        self.orbiter_wait_time = self.create_single_input(
            orbiter, "MAX_WAIT_TIME", self.config["ORBITER"]["MAX_WAIT_TIME"]
        )

        # Add EXCHANGES section
        self.create_category_header(right_column, "💱 EXCHANGES")
        exchanges = self.create_section(right_column, "EXCHANGES")

        # Exchange selection
        exchange_frame = ctk.CTkFrame(exchanges, fg_color=self.colors["frame_bg"])
        exchange_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            exchange_frame,
            text="Exchange:",
            width=200,
            anchor="w",
            font=("Helvetica", 12, "bold"),
            text_color=self.colors["text"],
        ).grid(row=0, column=0, padx=(10, 10), sticky="w")

        self.exchange_var = ctk.StringVar(value=self.config["EXCHANGES"]["name"])
        exchange_combobox = ctk.CTkComboBox(
            exchange_frame,
            values=["OKX", "BITGET"],
            variable=self.exchange_var,
            width=self.input_sizes["medium"],
            font=("Helvetica", 12, "bold"),
            fg_color=self.colors["entry_bg"],
            text_color=self.colors["text"],
            border_color=self.colors["accent"],
        )
        exchange_combobox.grid(row=0, column=1, padx=(0, 10), sticky="e")

        # API credentials
        self.exchange_api_key = self.create_single_input(
            exchanges,
            "API Key",
            self.config["EXCHANGES"]["apiKey"],
            width=self.input_sizes["extra_large"],
        )
        self.exchange_secret_key = self.create_single_input(
            exchanges,
            "Secret Key",
            self.config["EXCHANGES"]["secretKey"],
            width=self.input_sizes["extra_large"],
        )
        self.exchange_passphrase = self.create_single_input(
            exchanges,
            "Passphrase",
            self.config["EXCHANGES"]["passphrase"],
            width=self.input_sizes["extra_large"],
        )

        # Withdrawal settings
        withdrawal_frame = ctk.CTkFrame(exchanges, fg_color=self.colors["frame_bg"])
        withdrawal_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            withdrawal_frame,
            text="Withdrawal Settings",
            font=("Helvetica", 14, "bold"),
            text_color=self.colors["accent"],
        ).pack(anchor="w", padx=10, pady=10)

        # Currency selection (currently only ETH)
        self.withdrawal_currency = self.create_single_input(
            withdrawal_frame,
            "Currency",
            self.config["EXCHANGES"]["withdrawals"][0]["currency"],
            width=self.input_sizes["small"],
        )

        # Networks selection
        self.withdrawal_networks = self.create_network_checkboxes(
            withdrawal_frame,
            "Networks",
            self.config["EXCHANGES"]["withdrawals"][0]["networks"],
        )

        # Min/Max amount
        self.withdrawal_min_amount, self.withdrawal_max_amount = (
            self.create_range_inputs(
                withdrawal_frame,
                "Amount Range",
                [
                    self.config["EXCHANGES"]["withdrawals"][0]["min_amount"],
                    self.config["EXCHANGES"]["withdrawals"][0]["max_amount"],
                ],
            )
        )

        # Max wallet balance
        self.withdrawal_max_balance = self.create_single_input(
            withdrawal_frame,
            "Max Wallet Balance",
            self.config["EXCHANGES"]["withdrawals"][0].get("max_balance", 1.0),
            width=self.input_sizes["small"],
        )

        # Wait for funds checkbox and max wait time
        self.withdrawal_wait = self.create_checkbox(
            withdrawal_frame,
            "Wait for Funds to Arrive",
            self.config["EXCHANGES"]["withdrawals"][0]["wait_for_funds"],
        )
        self.withdrawal_wait_time = self.create_single_input(
            withdrawal_frame,
            "Max Wait Time (seconds)",
            self.config["EXCHANGES"]["withdrawals"][0]["max_wait_time"],
            width=self.input_sizes["small"],
        )

        # Retries
        self.withdrawal_retries = self.create_single_input(
            withdrawal_frame,
            "Retries",
            self.config["EXCHANGES"]["withdrawals"][0]["retries"],
            width=self.input_sizes["tiny"],
        )

        # Add NOSTRA section
        nostra = self.create_section(right_column, "NOSTRA")
        self.nostra_deposit_min, self.nostra_deposit_max = self.create_range_inputs(
            nostra,
            "PERCENT_OF_BALANCE_TO_DEPOSIT",
            self.config["NOSTRA"]["PERCENT_OF_BALANCE_TO_DEPOSIT"],
        )
        self.nostra_deposit = self.create_checkbox(
            nostra,
            "DEPOSIT",
            self.config["NOSTRA"]["DEPOSIT"],
        )
        self.nostra_borrow = self.create_checkbox(
            nostra,
            "BORROW",
            self.config["NOSTRA"]["BORROW"],
        )
        self.nostra_repay = self.create_checkbox(
            nostra,
            "REPAY",
            self.config["NOSTRA"]["REPAY"],
        )
        self.nostra_withdraw = self.create_checkbox(
            nostra,
            "WITHDRAW",
            self.config["NOSTRA"]["WITHDRAW"],
        )

        # Add NARWHAL_FINANCE section
        self.create_category_header(right_column, "💸 NARWHAL FINANCE")
        narwhal = self.create_section(right_column, "NARWHAL_FINANCE")

        # Проверяем существование раздела в конфиге
        if "NARWHAL_FINANCE" not in self.config:
            self.config["NARWHAL_FINANCE"] = {}

        self.narwhal_amount_min, self.narwhal_amount_max = self.create_range_inputs(
            narwhal,
            "AMOUNT_USDT_FOR_BET",
            self.config["NARWHAL_FINANCE"]["AMOUNT_USDT_FOR_BET"],
        )

        self.narwhal_bets_min, self.narwhal_bets_max = self.create_range_inputs(
            narwhal,
            "NUMBER_OF_BETS_PER_START",
            self.config["NARWHAL_FINANCE"]["NUMBER_OF_BETS_PER_START"],
        )

        self.narwhal_slots = self.create_checkbox(
            narwhal,
            "PLAY_SLOTS",
            self.config["NARWHAL_FINANCE"]["PLAY_SLOTS"],
        )

        self.narwhal_dice = self.create_checkbox(
            narwhal,
            "PLAY_DICE",
            self.config["NARWHAL_FINANCE"]["PLAY_DICE"],
        )

        self.narwhal_coinflip = self.create_checkbox(
            narwhal,
            "PLAY_COINFLIP",
            self.config["NARWHAL_FINANCE"]["PLAY_COINFLIP"],
        )

        # Add MADNESS section
        madness = self.create_section(right_column, "MADNESS")
        self.madness_swap_all = self.create_checkbox(
            madness,
            "SWAP_ALL_TO_MONAD",
            self.config["MADNESS"]["SWAP_ALL_TO_MONAD"],
        )

    def _save_and_close(self):
        """Save config and close the window"""
        self.save_config()
        self.root.destroy()

    def save_config(self):
        # Update config dictionary with new values
        # SETTINGS
        self.config["SETTINGS"]["THREADS"] = int(self.threads_entry.get())
        self.config["SETTINGS"]["ATTEMPTS"] = int(self.attempts_entry.get())
        self.config["SETTINGS"]["ACCOUNTS_RANGE"] = [
            int(self.acc_range_start.get()),
            int(self.acc_range_end.get()),
        ]

        # Add new SETTINGS fields
        self.config["SETTINGS"]["EXACT_ACCOUNTS_TO_USE"] = [
            int(x.strip()) for x in self.exact_accounts.get().split(",") if x.strip()
        ]

        # Паузы в секундах (целые числа)
        self.config["SETTINGS"]["PAUSE_BETWEEN_ATTEMPTS"] = [
            int(float(self.pause_attempts_min.get())),
            int(float(self.pause_attempts_max.get())),
        ]
        self.config["SETTINGS"]["PAUSE_BETWEEN_SWAPS"] = [
            int(float(self.pause_swaps_min.get())),
            int(float(self.pause_swaps_max.get())),
        ]
        self.config["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACCOUNTS"] = [
            int(float(self.pause_accounts_min.get())),
            int(float(self.pause_accounts_max.get())),
        ]
        self.config["SETTINGS"]["RANDOM_PAUSE_BETWEEN_ACTIONS"] = [
            int(float(self.pause_actions_min.get())),
            int(float(self.pause_actions_max.get())),
        ]
        self.config["SETTINGS"]["RANDOM_INITIALIZATION_PAUSE"] = [
            int(float(self.init_pause_min.get())),
            int(float(self.init_pause_max.get())),
        ]

        self.config["SETTINGS"]["BROWSER_PAUSE_MULTIPLIER"] = float(
            self.browser_multiplier.get()
        )

        self.config["SETTINGS"]["TELEGRAM_USERS_IDS"] = [
            int(x.strip()) for x in self.telegram_ids.get().split(",") if x.strip()
        ]
        self.config["SETTINGS"]["TELEGRAM_BOT_TOKEN"] = self.telegram_token.get()

        # FAUCET
        self.config["FAUCET"]["NOCAPTCHA_API_KEY"] = self.nocaptcha_key.get()
        self.config["FAUCET"]["PROXY_FOR_NOCAPTCHA"] = self.proxy_nocaptcha.get()
        self.config["FAUCET"]["USE_CAPSOLVER_FOR_CLOUDFLARE"] = bool(
            self.use_capsolver.get()
        )
        self.config["FAUCET"]["CAPSOLVER_API_KEY"] = self.capsolver_key.get()

        # Добавляем поля для Solvium, которые есть в config.py
        if "USE_SOLVIUM_FOR_CLOUDFLARE" not in self.config["FAUCET"]:
            self.config["FAUCET"]["USE_SOLVIUM_FOR_CLOUDFLARE"] = False
        if "SOLVIUM_API_KEY" not in self.config["FAUCET"]:
            self.config["FAUCET"]["SOLVIUM_API_KEY"] = ""

        # DISPERSE
        self.config["DISPERSE"]["MIN_BALANCE_FOR_DISPERSE"] = [
            float(self.min_balance_min.get()),
            float(self.min_balance_max.get()),
        ]

        # DUSTED
        self.config["DUSTED"]["CLAIM"] = True if self.dusted_claim.get() else False
        self.config["DUSTED"]["SKIP_TWITTER_VERIFICATION"] = (
            True if self.dusted_skip_twitter_verification.get() else False
        )

        # FLOW
        self.config["FLOW"]["NUMBER_OF_SWAPS"] = [
            int(float(self.swaps_min.get())),
            int(float(self.swaps_max.get())),
        ]
        self.config["FLOW"]["PERCENT_OF_BALANCE_TO_SWAP"] = [
            int(float(self.balance_swap_min.get())),
            int(float(self.balance_swap_max.get())),
        ]

        # APRIORI
        self.config["APRIORI"]["AMOUNT_TO_STAKE"] = [
            float(self.apriori_stake_min.get()),
            float(self.apriori_stake_max.get()),
        ]
        self.config["APRIORI"]["STAKE"] = True if self.apriori_stake.get() else False
        self.config["APRIORI"]["UNSTAKE"] = (
            True if self.apriori_unstake.get() else False
        )

        # MAGMA
        self.config["MAGMA"]["AMOUNT_TO_STAKE"] = [
            float(self.magma_stake_min.get()),
            float(self.magma_stake_max.get()),
        ]
        self.config["MAGMA"]["STAKE"] = True if self.magma_stake.get() else False
        self.config["MAGMA"]["UNSTAKE"] = True if self.magma_unstake.get() else False

        # KINTSU
        self.config["KINTSU"]["AMOUNT_TO_STAKE"] = [
            float(self.kintsu_stake_min.get()),
            float(self.kintsu_stake_max.get()),
        ]
        self.config["KINTSU"]["STAKE"] = True if self.kintsu_stake.get() else False
        self.config["KINTSU"]["UNSTAKE"] = True if self.kintsu_unstake.get() else False

        # GASZIP
        self.config["GASZIP"]["NETWORKS_TO_REFUEL_FROM"] = [
            network for network, var in self.gaszip_networks if var.get()
        ]
        self.config["GASZIP"]["AMOUNT_TO_REFUEL"] = [
            float(self.gaszip_amount_min.get()),
            float(self.gaszip_amount_max.get()),
        ]
        self.config["GASZIP"]["MINIMUM_BALANCE_TO_REFUEL"] = float(
            self.gaszip_min_balance.get()
        )
        self.config["GASZIP"]["WAIT_FOR_FUNDS_TO_ARRIVE"] = (
            True if self.gaszip_wait.get() else False
        )
        self.config["GASZIP"]["MAX_WAIT_TIME"] = int(self.gaszip_wait_time.get())
        self.config["GASZIP"]["BRIDGE_ALL"] = (
            True if self.gaszip_bridge_all.get() else False
        )
        self.config["GASZIP"]["BRIDGE_ALL_MAX_AMOUNT"] = float(
            self.gaszip_bridge_max.get()
        )

        # MEMEBRIDGE
        self.config["MEMEBRIDGE"]["NETWORKS_TO_REFUEL_FROM"] = [
            network for network, var in self.memebridge_networks if var.get()
        ]
        self.config["MEMEBRIDGE"]["AMOUNT_TO_REFUEL"] = [
            float(self.memebridge_amount_min.get()),
            float(self.memebridge_amount_max.get()),
        ]
        self.config["MEMEBRIDGE"]["MINIMUM_BALANCE_TO_REFUEL"] = float(
            self.memebridge_min_balance.get()
        )
        self.config["MEMEBRIDGE"]["WAIT_FOR_FUNDS_TO_ARRIVE"] = (
            True if self.memebridge_wait.get() else False
        )
        self.config["MEMEBRIDGE"]["MAX_WAIT_TIME"] = int(
            self.memebridge_wait_time.get()
        )
        self.config["MEMEBRIDGE"]["BRIDGE_ALL"] = (
            True if self.memebridge_bridge_all.get() else False
        )
        self.config["MEMEBRIDGE"]["BRIDGE_ALL_MAX_AMOUNT"] = float(
            self.memebridge_bridge_max.get()
        )

        # TESTNET_BRIDGE
        self.config["TESTNET_BRIDGE"]["NETWORKS_TO_REFUEL_FROM"] = [
            network for network, var in self.testnet_networks if var.get()
        ]
        self.config["TESTNET_BRIDGE"]["AMOUNT_TO_REFUEL"] = [
            float(self.testnet_amount_min.get()),
            float(self.testnet_amount_max.get()),
        ]
        self.config["TESTNET_BRIDGE"]["MINIMUM_BALANCE_TO_REFUEL"] = float(
            self.testnet_min_balance.get()
        )
        self.config["TESTNET_BRIDGE"]["WAIT_FOR_FUNDS_TO_ARRIVE"] = (
            True if self.testnet_wait.get() else False
        )
        self.config["TESTNET_BRIDGE"]["MAX_WAIT_TIME"] = int(
            self.testnet_wait_time.get()
        )
        self.config["TESTNET_BRIDGE"]["BRIDGE_ALL"] = (
            True if self.testnet_bridge_all.get() else False
        )
        self.config["TESTNET_BRIDGE"]["BRIDGE_ALL_MAX_AMOUNT"] = float(
            self.testnet_bridge_max.get()
        )

        # LILCHOGSTARS
        self.config["LILCHOGSTARS"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"] = [
            int(self.lilchog_amount_min.get()),
            int(self.lilchog_amount_max.get()),
        ]

        # MONADKING
        self.config["MONADKING"]["MAX_AMOUNT_FOR_EACH_ACCOUNT"] = [
            int(self.monadking_amount_min.get()),
            int(self.monadking_amount_max.get()),
        ]

        # MAGICEDEN
        self.config["MAGICEDEN"]["NFT_CONTRACTS"] = [
            x.strip()
            for x in self.magiceden_contracts.get("1.0", "end-1c").split("\n")
            if x.strip()
        ]

        # FRONT_RUNNER
        self.config["FRONT_RUNNER"]["MAX_AMOUNT_TRANSACTIONS_FOR_ONE_RUN"] = [
            int(self.max_transactions_for_one_run[0].get()),
            int(self.max_transactions_for_one_run[1].get()),
        ]
        self.config["FRONT_RUNNER"]["PAUSE_BETWEEN_TRANSACTIONS"] = [
            int(self.pause_between_transactions[0].get()),
            int(self.pause_between_transactions[1].get()),
        ]

        # SHMONAD
        self.config["SHMONAD"]["BUY_AND_STAKE_SHMON"] = (
            True if self.buy_stake.get() else False
        )
        self.config["SHMONAD"]["UNSTAKE_AND_SELL_SHMON"] = (
            True if self.unstake_sell.get() else False
        )
        self.config["SHMONAD"]["PERCENT_OF_BALANCE_TO_SWAP"] = [
            int(float(self.shmonad_percent_min.get())),
            int(float(self.shmonad_percent_max.get())),
        ]

        # ORBITER
        self.config["ORBITER"]["AMOUNT_TO_BRIDGE"] = [
            float(self.orbiter_amount_min.get()),
            float(self.orbiter_amount_max.get()),
        ]
        self.config["ORBITER"]["BRIDGE_ALL"] = True if self.bridge_all.get() else False
        self.config["ORBITER"]["WAIT_FOR_FUNDS_TO_ARRIVE"] = (
            True if self.orbiter_wait.get() else False
        )
        self.config["ORBITER"]["MAX_WAIT_TIME"] = int(self.orbiter_wait_time.get())

        # EXCHANGES
        self.config["EXCHANGES"]["name"] = self.exchange_var.get()
        self.config["EXCHANGES"]["apiKey"] = self.exchange_api_key.get()
        self.config["EXCHANGES"]["secretKey"] = self.exchange_secret_key.get()
        self.config["EXCHANGES"]["passphrase"] = self.exchange_passphrase.get()

        # Update withdrawals configuration
        self.config["EXCHANGES"]["withdrawals"] = [
            {
                "currency": self.withdrawal_currency.get(),
                "networks": [
                    network for network, var in self.withdrawal_networks if var.get()
                ],
                "min_amount": float(self.withdrawal_min_amount.get()),
                "max_amount": float(self.withdrawal_max_amount.get()),
                "max_balance": float(self.withdrawal_max_balance.get()),
                "wait_for_funds": True if self.withdrawal_wait.get() else False,
                "max_wait_time": int(self.withdrawal_wait_time.get()),
                "retries": int(self.withdrawal_retries.get()),
            }
        ]

        # NOSTRA
        self.config["NOSTRA"]["PERCENT_OF_BALANCE_TO_DEPOSIT"] = [
            float(self.nostra_deposit_min.get()),
            float(self.nostra_deposit_max.get()),
        ]
        self.config["NOSTRA"]["DEPOSIT"] = True if self.nostra_deposit.get() else False
        self.config["NOSTRA"]["BORROW"] = True if self.nostra_borrow.get() else False
        self.config["NOSTRA"]["REPAY"] = True if self.nostra_repay.get() else False
        self.config["NOSTRA"]["WITHDRAW"] = (
            True if self.nostra_withdraw.get() else False
        )

        # NARWHAL_FINANCE
        if "NARWHAL_FINANCE" not in self.config:
            self.config["NARWHAL_FINANCE"] = {}

        self.config["NARWHAL_FINANCE"]["AMOUNT_USDT_FOR_BET"] = [
            int(float(self.narwhal_amount_min.get())),
            int(float(self.narwhal_amount_max.get())),
        ]

        self.config["NARWHAL_FINANCE"]["NUMBER_OF_BETS_PER_START"] = [
            int(float(self.narwhal_bets_min.get())),
            int(float(self.narwhal_bets_max.get())),
        ]

        self.config["NARWHAL_FINANCE"]["PLAY_SLOTS"] = (
            True if self.narwhal_slots.get() else False
        )

        self.config["NARWHAL_FINANCE"]["PLAY_DICE"] = (
            True if self.narwhal_dice.get() else False
        )

        self.config["NARWHAL_FINANCE"]["PLAY_COINFLIP"] = (
            True if self.narwhal_coinflip.get() else False
        )

        # MADNESS
        self.config["MADNESS"]["SWAP_ALL_TO_MONAD"] = (
            True if self.madness_swap_all.get() else False
        )

        # Save to file with improved formatting
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")

        # Custom YAML dumper for better formatting
        class OrderedDumper(yaml.SafeDumper):
            pass

        def dict_representer(dumper, data):
            # For the withdrawal dictionary inside EXCHANGES, use a specific order
            if isinstance(data, dict) and any(
                key in data for key in ["min_amount", "max_amount", "max_wait_time"]
            ):
                # This appears to be a withdrawal configuration
                ordered_items = []
                # Ensure currency comes first if present
                if "currency" in data:
                    ordered_items.append(("currency", data["currency"]))

                # Custom order for key withdrawal parameters
                order_priority = [
                    "networks",
                    "min_amount",
                    "max_amount",
                    "max_balance",
                    "wait_for_funds",
                    "max_wait_time",
                    "retries",
                ]

                for key in order_priority:
                    if key in data:
                        ordered_items.append((key, data[key]))

                # Add any remaining keys alphabetically
                for key in sorted(data.keys()):
                    if key not in ["currency"] and key not in order_priority:
                        ordered_items.append((key, data[key]))

                return dumper.represent_mapping(
                    yaml.resolver.Resolver.DEFAULT_MAPPING_TAG, ordered_items
                )

            # For all other dictionaries, sort keys alphabetically
            return dumper.represent_mapping(
                yaml.resolver.Resolver.DEFAULT_MAPPING_TAG, sorted(data.items())
            )

        OrderedDumper.add_representer(dict, dict_representer)

        with open(config_path, "w") as file:
            # Add a blank line between top-level sections
            yaml_text = yaml.dump(
                self.config,
                Dumper=OrderedDumper,
                default_flow_style=False,
                sort_keys=False,
                width=80,
            )

            # Insert blank lines between top-level sections for better readability
            formatted_lines = []
            prev_indent = None

            for line in yaml_text.split("\n"):
                current_indent = len(line) - len(line.lstrip())

                # If this is a top-level key (no indent) and not the first line
                if current_indent == 0 and line and prev_indent is not None:
                    formatted_lines.append("")  # Add a blank line before new section

                formatted_lines.append(line)
                prev_indent = current_indent if line else prev_indent

            file.write("\n".join(formatted_lines))

            print(f"Configuration saved to {config_path}")

    def run(self):
        """Run the configuration UI"""
        self.root.mainloop()


# Удалить или закомментировать эту часть, так как теперь запуск будет через метод run()
# def main():
#     app = ConfigUI()
#     app.root.mainloop()


# if __name__ == "__main__":
#     main()

#     app.root.mainloop()


# if __name__ == "__main__":
#     main()
