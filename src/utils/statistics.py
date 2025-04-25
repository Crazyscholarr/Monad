from tabulate import tabulate
from typing import List, Optional
from loguru import logger
import pandas as pd
from datetime import datetime
import os

from src.utils.config import Config, WalletInfo


def print_wallets_stats(config: Config, excel_path: str = "data/progress.xlsx"):
    """
    Выводит статистику по всем кошелькам в виде таблицы и сохраняет в Excel файл

    Args:
        config: Конфигурация с данными кошельков
        excel_path: Путь для сохранения Excel файла (по умолчанию "data/progress.xlsx")
    """
    try:
        # Сортируем кошельки по индексу
        sorted_wallets = sorted(config.WALLETS.wallets, key=lambda x: x.account_index)

        # Подготавливаем данные для таблицы
        table_data = []
        total_balance = 0
        total_transactions = 0

        for wallet in sorted_wallets:
            # Маскируем приватный ключ (последние 5 символов)
            masked_key = "•" * 3 + wallet.private_key[-5:]

            total_balance += wallet.balance
            total_transactions += wallet.transactions

            row = [
                str(wallet.account_index),  # Просто номер без ведущего нуля
                wallet.address,  # Полный адрес
                masked_key,
                f"{wallet.balance:.4f} MON",
                f"{wallet.transactions:,}",  # Форматируем число с разделителями
            ]
            table_data.append(row)

        # Если есть данные - выводим таблицу и статистику
        if table_data:
            # Создаем заголовки для таблицы
            headers = [
                " Account",
                "Wallet Address",
                "Private Key",
                "Balance (MON)",
                "Total Txs",
            ]

            # Формируем таблицу с улучшенным форматированием
            table = tabulate(
                table_data,
                headers=headers,
                tablefmt="double_grid",  # Более красивые границы
                stralign="center",  # Центрирование строк
                numalign="center",  # Центрирование чисел
            )

            # Считаем средние значения
            wallets_count = len(sorted_wallets)
            avg_balance = total_balance / wallets_count
            avg_transactions = total_transactions / wallets_count

            # Выводим таблицу и статистику
            logger.info(
                f"\n{'='*50}\n"
                f"         Wallets Statistics ({wallets_count} wallets)\n"
                f"{'='*50}\n"
                f"{table}\n"
                f"{'='*50}\n"
                f"{'='*50}"
            )

            logger.info(f"Average balance: {avg_balance:.4f} MON")
            logger.info(f"Average transactions: {avg_transactions:.1f}")
            logger.info(f"Total balance: {total_balance:.4f} MON")
            logger.info(f"Total transactions: {total_transactions:,}")

            # Сохраняем данные в Excel
            try:
                # Создаем директорию, если она не существует
                os.makedirs(os.path.dirname(excel_path), exist_ok=True)

                # Создаем DataFrame для Excel
                df_data = []
                for i, wallet in enumerate(sorted_wallets):
                    df_data.append(
                        {
                            "№ Account": wallet.account_index,
                            "Wallet Address": wallet.address,
                            "Private Key": masked_key,
                            "Balance (MON)": wallet.balance,
                            "Total Txs": wallet.transactions,
                        }
                    )

                df = pd.DataFrame(df_data)

                # Добавляем итоговую строку
                summary_df = pd.DataFrame(
                    [
                        {
                            " Account": "TOTAL",
                            "Wallet Address": f"Wallets: {wallets_count}",
                            "Private Key": "",
                            "Balance (MON)": total_balance,
                            "Total Txs": total_transactions,
                        }
                    ]
                )

                # Добавляем строку со средними значениями
                avg_df = pd.DataFrame(
                    [
                        {
                            "Account": "AVERAGE",
                            "Wallet Address": "",
                            "Private Key": "",
                            "Balance (MON)": avg_balance,
                            "Total Txs": avg_transactions,
                        }
                    ]
                )

                # Объединяем все в один DataFrame
                result_df = pd.concat([df, summary_df, avg_df], ignore_index=True)

                # Создаем имя файла с датой и временем
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                file_dir = os.path.dirname(excel_path)
                file_name = f"progress_{timestamp}.xlsx"
                output_path = os.path.join(file_dir, file_name)

                # Сохраняем в Excel
                result_df.to_excel(output_path, index=False)
                logger.info(f"Statistics saved to Excel file: {output_path}")

            except Exception as excel_error:
                logger.error(f"Error saving to Excel: {excel_error}")
        else:
            logger.info("\nNo wallet statistics available")

    except Exception as e:
        logger.error(f"Error while printing statistics: {e}")
