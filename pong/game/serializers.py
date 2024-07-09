from rest_framework import serializers
from .models import Game, Tournament

class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'player1', 'player2', 'score', 'mode', 'tournament', 'created_at']

    def validate_mode(self, value):
        if value != '1VS1':
            raise serializers.ValidationError("Game mode must be '1VS1'")
        return value

class TournamentGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['player1', 'player2', 'score', 'mode']

    def validate_mode(self, value):
        if value != 'TOURNAMENT':
            raise serializers.ValidationError("Game mode must be 'TOURNAMENT'")
        return value

class TournamentSerializer(serializers.ModelSerializer):
    game1 = TournamentGameSerializer()
    game2 = TournamentGameSerializer()
    game3 = TournamentGameSerializer()

    class Meta:
        model = Tournament
        fields = ['game1', 'game2', 'game3']

    def create(self, validated_data):
        game1_data = validated_data.pop('game1')
        game2_data = validated_data.pop('game2')
        game3_data = validated_data.pop('game3')

        tournament = Tournament.objects.create(**validated_data)

        game1 = Game.objects.create(tournament=tournament, **game1_data)
        game2 = Game.objects.create(tournament=tournament, **game2_data)
        game3 = Game.objects.create(tournament=tournament, **game3_data)

        tournament.game1 = game1
        tournament.game2 = game2
        tournament.game3 = game3
        tournament.save()

        return tournament
