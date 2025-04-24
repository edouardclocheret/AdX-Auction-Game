from agt_server.agents.base_agents.adx_agent import NDaysNCampaignsAgent
from agt_server.agents.test_agents.adx.tier1.my_agent import Tier1NDaysNCampaignsAgent
from agt_server.local_games.adx_arena import AdXGameSimulator
from agt_server.agents.utils.adx.structures import Bid, Campaign, BidBundle
from typing import Set, Dict
# import random

class MyNDaysNCampaignsAgent(NDaysNCampaignsAgent):

    def __init__(self):
        super().__init__()
        self.name = "smart_stratA"

    def on_new_game(self) -> None:
        self.training_logs = []

    def get_campaign_bids(self, campaigns_for_auction: Set[Campaign]) -> Dict[Campaign, float]:
        bids = {}
        quality = self.get_quality_score()
        current_day = self.get_current_day()

        for campaign in campaigns_for_auction:
            duration = campaign.end_day - campaign.start_day + 1
            value_per_day = campaign.reach / duration  # 评估密度价值
            urgency_factor = 1.2 if current_day >= campaign.end_day - 1 else 1.0
            base_value = value_per_day * urgency_factor

            # 设置目标 effective bid（逆推真实 bid）
            effective_bid_target = base_value * 0.8  # 稍低于潜在价值，避免质量分数太差时中标无利可图
            bid = effective_bid_target * quality
            bid = self.clip_campaign_bid(campaign, bid)
            bids[campaign] = bid

        return bids

    def get_ad_bids(self) -> Set[BidBundle]:
        bundles = set()

        for campaign in self.get_active_campaigns():
            try:
                reach = self.get_cumulative_reach(campaign)
                cost = self.get_cumulative_cost(campaign)
                remaining_reach = max(1, campaign.reach - reach)
                remaining_budget = max(1.0, campaign.budget - cost)
                
                if campaign.reach == 0:
                    print(f"[WARNING] Campaign {campaign.uid} has 0 reach.")

                progress = reach / campaign.reach if campaign.reach != 0 else 0.0

                if progress > 0.8:
                    boost = 1.2
                elif progress < 0.3:
                    boost = 0.8
                else:
                    boost = 1.0

                bid_per_item = max(0.1, (remaining_budget / remaining_reach) * boost)
                total_limit = remaining_budget
                
                bid_per_item = min(bid_per_item, total_limit)#fix bugs

                seg = campaign.target_segment
                if seg is None:
                    raise ValueError("Target segment is None")

                bid_entries = {Bid(
                    bidder=self,
                    auction_item=seg,
                    bid_per_item=bid_per_item,
                    bid_limit=total_limit
                )}

                bundle = BidBundle(campaign.uid, total_limit, bid_entries)
                bundles.add(bundle)

            except Exception as e:
                import traceback
                print(f"[ERROR] Failed to bid for campaign {campaign.uid} - {type(e).__name__}: {e}")
                traceback.print_exc()


        return bundles


my_agent_submission = MyNDaysNCampaignsAgent()

if __name__ == "__main__":
    test_agents = [MyNDaysNCampaignsAgent()] + [Tier1NDaysNCampaignsAgent(name=f"Agent {i+1}") for i in range(9)]
    simulator = AdXGameSimulator()
    simulator.run_simulation(agents=test_agents, num_simulations=500)
