

def game_states_equivalent(game_state_1, game_state_2):
    def dicts_equivalent(dict1, dict2):
        if set(dict1.keys()) != set(dict2.keys()):
            return False
        return all(dict1[k] == dict2[k] for k in dict1)

    return (
        game_state_1.cash == game_state_2.cash
        and game_state_1.time == game_state_2.time
        and game_state_1.horizon == game_state_2.horizon
        and dicts_equivalent(game_state_1.assets, game_state_2.assets)
        and dicts_equivalent(game_state_1.expired_assets, game_state_2.expired_assets)
    )


def get_asset_cash_flow(asset, action):
    if asset.state == "On Market":
        return asset.revenue_this_step
    elif asset.state == "In Development" or (
        asset.state == "Idle" and action == "invest"
    ):
        return -asset.cost_this_step
    return 0.0