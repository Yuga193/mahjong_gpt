import os
import json
import random
import dotenv
import openai
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

# .envファイルから環境変数を読み込む
dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_gpt_commentary(doraA, hand, player_wind, round_wind, selectedTile):
    prompt = (f"""
自風: {player_wind}, 場風: {round_wind}<br>
ドラ: {doraA}<br>
捨て牌: {selectedTile}<br>
手牌: {hand}<br><br>

手牌を表示する際は ["1m", "2m", "3m", "1p", "2p", "3p", "1s", "2s", "3s", "東", "南", "白", "發", "中"] ではなく、 [1m, 2m, 3m, 1p, 2p, 3p, 1s, 2s, 3s, 東, 南, 白, 發, 中] の形式で表示してください。<br>
文中に * を使用しないでください。<br>
自風、場風、ドラ、捨て牌、手牌のそれぞれの項目の後に "<br>" をつけて改行してください。<br>
手牌の改行には、 "<br>" を2回挿入し、手牌表示の前後で改行を行ってください。<br>
解説の冒頭で、結論として最適な捨て牌を先に提示してください。その後、その理由を簡潔に説明してください。説明は冗長にならないようにしてください。
**巡目や局の進行状況については考慮せず、現在の手牌に基づいて分析を行ってください。推測による判断は行わないでください。

解説を行う際、以下の要素を考慮してください。
順子と刻子を優先して残し、待ちの形（両面待ち、カンチャン待ち、ペンチャン待ちなど）を崩さないようにする。
役牌（東、南、西、北、白、發、中）は、重なる可能性を考慮しつつも、孤立牌である場合は優先して処理する。
ドラの活用: 手牌にドラがある場合、最大限生かすように判断する。手牌にドラがない場合は効率重視。
手牌の効率: 孤立している牌や無駄牌を優先して切る。リャンメン待ちが崩れないようにすることが大切。
高得点の手や役の可能性: 一盃口や三色などの役を意識し、役が狙える形は優先して残す。
安全性と防御: 必要に応じて、終盤に向けて安全牌を意識して残す。

"""
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは麻雀の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error occurred while generating commentary: {str(e)}"
# 麻雀の全牌リスト
ALL_TILES = [tile for tile in [
    "1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
    "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p",
    "1s", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s",
    "東", "南", "西", "北", "白", "發", "中"
] for _ in range(4)]  # 各牌を4枚ずつ持つようにリストを拡張

# 手牌をランダムに生成する関数
def generate_random_hand():
    tiles = random.sample(ALL_TILES, k=24)  # 重複なしで24枚の牌を選ぶ
    doraA = tiles[0]  # ユーザーが見えるドラ
    doraB = tiles[1:5]  # 存在してるがユーザーからは見えないドラ
    ura_dora = tiles[5:10]  # 次の5枚を裏ドラとする
    hand = tiles[10:]  # 残りの牌を手牌とする

    player_wind = random.choice(["東", "南", "西", "北"])
    round_wind = random.choice(["東", "南"])

    return hand, doraA, doraB, ura_dora, player_wind, round_wind

class QuestionView(TemplateView):
    template_name = 'question.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hand, doraA, doraB, ura_dora, player_wind, round_wind = generate_random_hand()  # 手牌、ドラ、裏ドラ、自風、場風を取得
        context['hand'] = hand
        context['doraA'] = doraA
        context['doraB'] = doraB
        context['ura_dora'] = ura_dora
        context['player_wind'] = player_wind
        context['round_wind'] = round_wind
        return context

@csrf_exempt
def analyze_hand(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            selectedTile = data.get('selectedTile')
            hand = json.loads(data.get('hand'))
            doraA = data.get("doraA")
            player_wind = data.get("playerWind")
            round_wind = data.get("roundWind")

            commentary = ""
            # ChatGPT APIを呼び出して講評を取得
            gpt_commentary = get_gpt_commentary(doraA, hand, player_wind, round_wind, selectedTile)
            commentary += f"{gpt_commentary}"  # ここでGPTの講評を追加

            response_data = {
                'commentary': commentary,
                'gpt_commentary': gpt_commentary,
                'player_wind': player_wind,
                'round_wind': round_wind,
                'doraA': doraA,
                'selectedTile': selectedTile,
                'hand': hand,
                'display_info': f"自風: {player_wind}, 場風: {round_wind}, ドラ: {doraA}, 手牌: {hand}, 捨牌: {selectedTile}"
            }

            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)