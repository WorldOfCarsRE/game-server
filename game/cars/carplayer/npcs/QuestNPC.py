from game.cars.ai import QuestConstants

from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_QUERY_INTERACTIONS,
    COMMAND_OFFER_QUEST_PASSIVE, COMMAND_OFFER_QUEST_ACCEPT,
    CMD_TYPE_NEGATIVE, TYPE_NPC,
    COMMAND_OFFER_QUEST_COMPLETE)

import time

class QuestNPC:

    def requestInteract(npc, av, eventId: int, args: list) -> None:
        currentQuest = 0
        questRules = []
        readyToTurnIn = False
        questCompleted = False

        for questId, ruleData in QuestConstants.QUESTS.get(npc.getAssetId(), {}).items():
            questCompleted = av.hasRuleId(ruleData[2])

            if not questCompleted:
                currentQuest = questId
                questRules = ruleData
                readyToTurnIn = av.hasRuleId(ruleData[0])
                break

        npc.catalogId = currentQuest

        # Indicators: First visit (32024), Available quest (32025), Incomplete quest (32026), Complete quest (32027)
        indicatorId = 32025

        commandId = COMMAND_OFFER_QUEST_PASSIVE if currentQuest in av.getActiveQuests() else COMMAND_OFFER_QUEST_ACCEPT
        commandType = CMD_TYPE_POSITIVE

        if readyToTurnIn:
            indicatorId = 32027

            commandId = COMMAND_OFFER_QUEST_COMPLETE

        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            if not questCompleted:
                npc.d_broadcastChoreographyToPlayer(av.doId, [], [], [[indicatorId, 0]], [])

        elif eventId == COMMAND_OFFER_QUEST_ACCEPT:
            av.addActiveQuest(npc.getCatalogId())

            commandId = COMMAND_OFFER_QUEST_PASSIVE
            commandType = CMD_TYPE_NEGATIVE

            # Change indicator
            indicatorId = 32026

            npc.d_broadcastChoreographyToPlayer(av.doId, [], [], [[indicatorId, 0]], [])

        elif eventId == COMMAND_OFFER_QUEST_COMPLETE:
            if args[0] == npc.getCatalogId():
                QuestNPC.giveRewards(av, args[0])

                av.addRuleState(questRules[1], 1, 1, int(time.time()))

                av.addRuleState(questRules[2], 1, 1, int(time.time()))

                av.d_setRuleStates(av.ruleStates)

                av.removeActiveQuest(currentQuest)

                # Reset indicator
                npc.d_broadcastChoreographyToPlayer(av.doId, [], [], [[0, 0]], [])

                commandType = CMD_TYPE_NEGATIVE

        data = [eventId, npc.getCatalogId(), commandType]

        if not questCompleted and eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            data[0] = commandId

        npc.d_setInteractiveCommands(av.doId, eventId, data)

    def giveRewards(av, questId: int) -> None:
        rewards = QuestConstants.REWARDS.get(questId)

        if not rewards:
            return

        for rewardType, value in rewards.items():
            match rewardType:
                case "coins":
                    av.addCoins(value)
                case "paints":
                    paints: list = av.racecar.getPaints()

                    for paint in value:
                        paints.append(paint)

                    av.racecar.setPaints(paints)
