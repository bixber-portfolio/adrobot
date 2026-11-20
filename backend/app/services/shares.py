from dataclasses import dataclass, replace

TOTAL_SHARE = 100  # доли активных офферов потока в сумме, в процентах


class ShareError(ValueError):
    """Доли нельзя рассчитать: данные заведомо неверные."""


@dataclass
class OfferShare:
    offer_id: int
    share: int = 0
    pinned: bool = False
    removed: bool = False


def _validate(active: list[OfferShare], pinned: list[OfferShare]) -> int:
    """Проверяет входные данные и возвращает сумму закреплённых долей."""
    if len(active) > TOTAL_SHARE:
        raise ShareError(
            f"Офферов больше {TOTAL_SHARE}: каждому не хватит по проценту"
        )
    for offer in pinned:
        if not 0 <= offer.share <= TOTAL_SHARE:
            raise ShareError(
                f"Оффер {offer.offer_id}: "
                f"доля должна быть от 0 до {TOTAL_SHARE}"
            )
    pinned_sum = sum(o.share for o in pinned)
    if pinned_sum > TOTAL_SHARE:
        raise ShareError(
            f"Закреплённые доли дают {pinned_sum}, "
            f"а это больше {TOTAL_SHARE}"
        )
    return pinned_sum


def _can_keep_pins(
    active_count: int, free_count: int, pinned_sum: int
) -> bool:
    if free_count == 0:
        return pinned_sum == TOTAL_SHARE or active_count == 0
    # Каждому незакреплённому должно достаться хотя бы по проценту.
    return TOTAL_SHARE - pinned_sum >= free_count


def recalculate_shares(offers: list[OfferShare]) -> list[OfferShare]:
    """Возвращает новый список: доли активных офферов в сумме дают 100.

    Удалённые получают 0. Закреплённые сохраняют свою долю, остаток делится
    поровну между остальными (лишние единицы идут первым). Если с
    закреплёнными получить 100 нельзя, закрепления снимаются и делится
    поровну между всеми.
    """
    active = [o for o in offers if not o.removed]
    pinned = [o for o in active if o.pinned]
    pinned_sum = _validate(active, pinned)

    free_count = len(active) - len(pinned)
    keep_pins = _can_keep_pins(len(active), free_count, pinned_sum)
    if keep_pins:
        distributed, fixed_sum = free_count, pinned_sum
    else:
        distributed, fixed_sum = len(active), 0
    base, extra = divmod(TOTAL_SHARE - fixed_sum, distributed or 1)

    result = []
    position = 0
    for offer in offers:
        if offer.removed:
            result.append(replace(offer, share=0))
        elif offer.pinned and keep_pins:
            result.append(replace(offer))
        else:
            share = base + (1 if position < extra else 0)
            position += 1
            result.append(replace(offer, share=share, pinned=False))
    return result
