"""
Service for generating compliments for healthy food choices.
"""
import random
from typing import List, Optional
from models.nutrition_models import FoodItem


class ComplimentService:
    """Service for identifying healthy foods and generating compliments"""
    
    # Categories of healthy foods (English and Russian)
    HEALTHY_FOODS = {
        'vegetables': [
            'spinach', 'broccoli', 'kale', 'lettuce', 'arugula', 'cucumber', 'tomato', 
            'bell pepper', 'carrot', 'celery', 'zucchini', 'squash', 'asparagus',
            'brussels sprouts', 'cauliflower', 'cabbage', 'onion', 'garlic', 'leek',
            'radish', 'beet', 'turnip', 'sweet potato', 'pumpkin', 'eggplant',
            'artichoke', 'mushroom', 'collard', 'chard', 'watercress', 'bok choy',
            # Russian names
            'шпинат', 'брокколи', 'капуста', 'салат', 'огурец', 'помидор', 'томат',
            'перец', 'морковь', 'сельдерей', 'кабачок', 'тыква', 'спаржа',
            'цветная капуста', 'лук', 'чеснок', 'редис', 'свекла', 'репа',
            'батат', 'баклажан', 'артишок', 'грибы', 'гриб'
        ],
        'fruits': [
            'apple', 'banana', 'orange', 'berries', 'strawberry', 'blueberry', 
            'raspberry', 'blackberry', 'grape', 'melon', 'watermelon', 'cantaloupe',
            'pear', 'peach', 'plum', 'apricot', 'cherry', 'kiwi', 'mango', 'papaya',
            'pineapple', 'avocado', 'lemon', 'lime', 'grapefruit', 'pomegranate',
            'cranberry', 'fig', 'date', 'prune', 'raisin',
            # Russian names
            'яблоко', 'банан', 'апельсин', 'ягоды', 'клубника', 'черника',
            'малина', 'ежевика', 'виноград', 'дыня', 'арбуз', 'дыня',
            'груша', 'персик', 'слива', 'абрикос', 'вишня', 'киви', 'манго',
            'ананас', 'авокадо', 'лимон', 'лайм', 'грейпфрут', 'гранат',
            'клюква', 'инжир', 'финик', 'чернослив', 'изюм'
        ],
        'whole_grains': [
            'quinoa', 'brown rice', 'oats', 'barley', 'buckwheat', 'millet',
            'whole wheat', 'whole grain', 'bulgur', 'farro', 'amaranth', 'teff',
            'wild rice', 'steel cut oats', 'rolled oats',
            # Russian names
            'киноа', 'бурый рис', 'овес', 'овсянка', 'ячмень', 'гречка', 'пшено',
            'цельная пшеница', 'цельное зерно', 'булгур', 'полба', 'амарант',
            'дикий рис', 'овсяные хлопья'
        ],
        'lean_proteins': [
            'chicken breast', 'turkey breast', 'fish', 'salmon', 'tuna', 'cod',
            'tilapia', 'sardines', 'mackerel', 'tofu', 'tempeh', 'legumes', 'beans',
            'lentils', 'chickpeas', 'black beans', 'kidney beans', 'pinto beans',
            'navy beans', 'lima beans', 'edamame', 'egg whites', 'lean beef',
            'lean pork', 'shellfish', 'crab', 'shrimp', 'lobster',
            # Russian names
            'куриная грудка', 'грудка индейки', 'рыба', 'лосось', 'тунец', 'треска',
            'сардины', 'скумбрия', 'тофу', 'темпе', 'бобовые', 'фасоль',
            'чечевица', 'нут', 'черная фасоль', 'красная фасоль',
            'белая фасоль', 'эдамаме', 'яичные белки', 'постная говядина',
            'постная свинина', 'морепродукты', 'краб', 'креветки', 'омар'
        ],
        'healthy_fats': [
            'avocado', 'nuts', 'almonds', 'walnuts', 'pecans', 'cashews', 'pistachios',
            'brazil nuts', 'hazelnuts', 'seeds', 'chia seeds', 'flax seeds', 
            'pumpkin seeds', 'sunflower seeds', 'sesame seeds', 'olive oil',
            'coconut oil', 'nut butter', 'almond butter', 'peanut butter',
            # Russian names
            'авокадо', 'орехи', 'миндаль', 'грецкие орехи', 'пекан', 'кешью',
            'фисташки', 'бразильские орехи', 'фундук', 'семена', 'семена чиа',
            'льняные семена', 'тыквенные семечки', 'подсолнечные семечки',
            'кунжутные семена', 'оливковое масло', 'кокосовое масло',
            'ореховое масло', 'миндальное масло', 'арахисовое масло'
        ],
        'dairy_alternatives': [
            'greek yogurt', 'cottage cheese', 'kefir', 'almond milk', 'oat milk',
            'soy milk', 'coconut milk', 'cashew milk', 'low fat milk', 'skim milk',
            # Russian names
            'греческий йогурт', 'творог', 'кефир', 'миндальное молоко', 'овсяное молоко',
            'соевое молоко', 'кокосовое молоко', 'молоко кешью', 'обезжиренное молоко',
            'молоко', 'йогурт'
        ]
    }
    
    # Compliment templates for different categories
    COMPLIMENTS = {
        'en': {
            'vegetables': [
                "Great choice with the {food}! 🥬 Packed with vitamins and fiber!",
                "Love seeing {food} on your plate! 🌿 Your body will thank you!",
                "Excellent vegetable choice with {food}! 🥕 So many nutrients!",
                "Fantastic! {food} is a nutritional powerhouse! 💚",
                "Way to go with the {food}! 🌱 Getting those essential vitamins!",
            ],
            'fruits': [
                "Wonderful choice with {food}! 🍎 Natural sweetness and vitamins!",
                "Love the {food}! 🍓 Antioxidants and natural energy!",
                "Great pick with {food}! 🥝 Nature's candy with benefits!",
                "Awesome! {food} brings natural vitamins and fiber! 🍊",
                "Excellent fruit choice with {food}! 🍌 Healthy and delicious!",
            ],
            'whole_grains': [
                "Fantastic choice with {food}! 🌾 Great source of complex carbs!",
                "Love the {food}! 💪 Sustained energy and fiber!",
                "Excellent grain choice! {food} provides lasting nutrition! 🌿",
                "Way to go with {food}! 🌾 Your energy levels will love this!",
                "Great pick! {food} offers wonderful nutritional benefits! ✨",
            ],
            'lean_proteins': [
                "Excellent protein choice with {food}! 💪 Building those muscles!",
                "Great pick with {food}! 🐟 Quality protein for your body!",
                "Love seeing {food}! 🏋️ Perfect for muscle recovery and growth!",
                "Fantastic protein source with {food}! 💪 Your muscles will thank you!",
                "Awesome choice! {food} provides excellent lean protein! 🌟",
            ],
            'healthy_fats': [
                "Smart choice with {food}! 🥑 Healthy fats for brain and heart!",
                "Love the {food}! 🧠 Great for cognitive function!",
                "Excellent healthy fat choice! {food} supports overall wellness! ✨",
                "Way to go with {food}! 💚 Your heart will love these healthy fats!",
                "Fantastic! {food} provides essential fatty acids! 🌟",
            ],
            'dairy_alternatives': [
                "Great choice with {food}! 🥛 Calcium and protein goodness!",
                "Love the {food}! 💪 Supporting bone health!",
                "Excellent pick! {food} provides quality nutrition! ✨",
                "Way to go with {food}! 🌟 Smart nutritional choice!",
                "Fantastic! {food} offers great nutritional benefits! 💚",
            ]
        },
        'ru': {
            'vegetables': [
                "Отличный выбор с {food}! 🥬 Полны витаминов и клетчатки!",
                "Рад видеть {food} на вашей тарелке! 🌿 Ваше тело скажет спасибо!",
                "Превосходный выбор овощей с {food}! 🥕 Столько питательных веществ!",
                "Фантастика! {food} - это питательная электростанция! 💚",
                "Так держать с {food}! 🌱 Получаете незаменимые витамины!",
            ],
            'fruits': [
                "Замечательный выбор с {food}! 🍎 Натуральная сладость и витамины!",
                "Обожаю {food}! 🍓 Антиоксиданты и натуральная энергия!",
                "Отличный выбор с {food}! 🥝 Природные сладости с пользой!",
                "Потрясающе! {food} приносит натуральные витамины и клетчатку! 🍊",
                "Превосходный выбор фруктов с {food}! 🍌 Полезно и вкусно!",
            ],
            'whole_grains': [
                "Фантастический выбор с {food}! 🌾 Отличный источник сложных углеводов!",
                "Обожаю {food}! 💪 Длительная энергия и клетчатка!",
                "Превосходный выбор зерновых! {food} обеспечивает долговременное питание! 🌿",
                "Так держать с {food}! 🌾 Ваши энергетические уровни полюбят это!",
                "Отличный выбор! {food} предлагает замечательные питательные преимущества! ✨",
            ],
            'lean_proteins': [
                "Превосходный выбор белка с {food}! 💪 Наращиваете мышцы!",
                "Отличный выбор с {food}! 🐟 Качественный белок для вашего тела!",
                "Рад видеть {food}! 🏋️ Идеально для восстановления и роста мышц!",
                "Фантастический источник белка с {food}! 💪 Ваши мышцы скажут спасибо!",
                "Потрясающий выбор! {food} обеспечивает превосходный постный белок! 🌟",
            ],
            'healthy_fats': [
                "Умный выбор с {food}! 🥑 Полезные жиры для мозга и сердца!",
                "Обожаю {food}! 🧠 Отлично для когнитивных функций!",
                "Превосходный выбор полезных жиров! {food} поддерживает общее благополучие! ✨",
                "Так держать с {food}! 💚 Ваше сердце полюбит эти полезные жиры!",
                "Фантастика! {food} обеспечивает незаменимые жирные кислоты! 🌟",
            ],
            'dairy_alternatives': [
                "Отличный выбор с {food}! 🥛 Кальций и белковая польза!",
                "Обожаю {food}! 💪 Поддерживает здоровье костей!",
                "Превосходный выбор! {food} обеспечивает качественное питание! ✨",
                "Так держать с {food}! 🌟 Умный пищевой выбор!",
                "Фантастика! {food} предлагает отличные питательные преимущества! 💚",
            ]
        }
    }
    
    # General healthy eating compliments
    GENERAL_COMPLIMENTS = {
        'en': [
            "You're making wonderful nutritional choices! 🌟",
            "Your body is getting amazing nutrients from this meal! 💚",
            "Love seeing such thoughtful food choices! ✨",
            "You're really taking care of your health! 🌿",
            "Excellent approach to balanced nutrition! 💪",
            "Your healthy eating habits are inspiring! 🌱",
            "Way to prioritize your wellness through food! 🌈",
            "These nutritious choices will fuel your day perfectly! ⚡",
        ],
        'ru': [
            "Вы делаете замечательный пищевой выбор! 🌟",
            "Ваше тело получает удивительные питательные вещества из этого блюда! 💚",
            "Рад видеть такой обдуманный выбор еды! ✨",
            "Вы действительно заботитесь о своём здоровье! 🌿",
            "Превосходный подход к сбалансированному питанию! 💪",
            "Ваши здоровые пищевые привычки вдохновляют! 🌱",
            "Так держать, приоритет здоровья через питание! 🌈",
            "Эти питательные выборы идеально зарядят ваш день! ⚡",
        ]
    }
    
    def identify_healthy_foods(self, food_items: List[FoodItem]) -> List[tuple]:
        """
        Identify healthy foods from the food items list.
        Returns list of tuples: (food_item, category)
        """
        healthy_items = []
        
        for item in food_items:
            food_name = item.name.lower()
            
            # Check each category
            for category, foods in self.HEALTHY_FOODS.items():
                for healthy_food in foods:
                    if healthy_food in food_name:
                        healthy_items.append((item, category))
                        break  # Move to next item once we find a match
        
        return healthy_items
    
    def generate_compliment(self, healthy_items: List[tuple], language: str = 'en') -> Optional[str]:
        """
        Generate a compliment based on identified healthy foods.
        Returns None if no healthy foods found.
        """
        if not healthy_items:
            return None
        
        # If multiple healthy items, choose one randomly to compliment
        if len(healthy_items) > 1:
            # Prefer specific compliments over general ones
            item, category = random.choice(healthy_items)
            compliment = random.choice(self.COMPLIMENTS[language][category])
            return compliment.format(food=item.name)
        else:
            # Single healthy item
            item, category = healthy_items[0]
            compliment = random.choice(self.COMPLIMENTS[language][category])
            return compliment.format(food=item.name)
    
    def generate_response_with_compliment(self, food_items: List[FoodItem], language: str = 'en') -> Optional[str]:
        """
        Generate a compliment response for the food items.
        Returns None if no healthy foods are identified.
        """
        healthy_items = self.identify_healthy_foods(food_items)
        
        if not healthy_items:
            return None
        
        # If we have multiple healthy items, sometimes give a general compliment
        if len(healthy_items) >= 3 and random.random() < 0.3:
            return random.choice(self.GENERAL_COMPLIMENTS[language])
        
        return self.generate_compliment(healthy_items, language)


# Global instance
compliment_service = ComplimentService()
