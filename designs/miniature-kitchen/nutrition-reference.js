/* Selected factual SR28 reference values. Unknowns and measurement assumptions remain explicit. */
window.KitchenNutritionReference = {
  "id": "usda-sr28-selected-2015-v1",
  "availableFrom": "2026-11-10",
  "release": "USDA SR28 September 2015",
  "source": {
    "label": "USDA SR28 선택 성분 · 2015년 자료의 공개 게시본",
    "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
    "notice": "현재 제품의 분석값이 아닌 가식부 100g 참고값. 원 제공처 직접 대조는 하지 못했습니다."
  },
  "waterNote": "자료의 수분은 g이며 기존 mL 수분 기록으로 자동 변환하지 않습니다.",
  "cookingNote": "조리 전 재료(밥은 조리된 밥) 합산 추정입니다. 조리 중 손실·흡수와 실제 계량량에 따라 달라집니다.",
  "items": [
    {
      "id": "01123",
      "name": "계란",
      "description": "Egg, whole, raw, fresh",
      "per100g": {
        "kcal": 143.0,
        "carb": 0.72,
        "protein": 12.56,
        "fat": 9.51,
        "fiber": 0.0,
        "water": null,
        "calcium": 56.0,
        "sodium": 142.0,
        "sugar": 0.37
      },
      "sourceWaterGrams": 76.15,
      "gramsPerUnit": {
        "개": 50,
        "알": 50
      },
      "assumption": "계란 1개는 큰 달걀의 껍질을 뺀 50g으로 계산",
      "source": {
        "label": "USDA SR28 · Egg, whole, raw, fresh",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "11282",
      "name": "양파",
      "description": "Onions, raw",
      "per100g": {
        "kcal": 40.0,
        "carb": 9.34,
        "protein": 1.1,
        "fat": 0.1,
        "fiber": 1.7,
        "water": null,
        "calcium": 23.0,
        "sodium": 4.0,
        "sugar": 4.24
      },
      "sourceWaterGrams": 89.11,
      "gramsPerUnit": {
        "개": 200
      },
      "assumption": "양파 1개를 200g으로 가정(기존 비용 계산과 같은 중량 가정)",
      "source": {
        "label": "USDA SR28 · Onions, raw",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "20453",
      "name": "밥/즉석밥",
      "description": "Rice, white, short-grain, cooked, unenriched",
      "per100g": {
        "kcal": 130.0,
        "carb": 28.73,
        "protein": 2.36,
        "fat": 0.19,
        "fiber": null,
        "water": null,
        "calcium": 1.0,
        "sodium": 0.0,
        "sugar": null
      },
      "sourceWaterGrams": 68.53,
      "gramsPerUnit": {
        "공기": 210
      },
      "assumption": "밥 1공기를 210g으로 가정. 미국 단립종 조리된 흰쌀밥 참고값이며 특정 즉석밥 제품값 아님",
      "source": {
        "label": "USDA SR28 · Rice, white, short-grain, cooked, unenriched",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "05062",
      "name": "닭가슴살",
      "description": "Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw",
      "per100g": {
        "kcal": 120.0,
        "carb": 0.0,
        "protein": 22.5,
        "fat": 2.62,
        "fiber": 0.0,
        "water": null,
        "calcium": 5.0,
        "sodium": 45.0,
        "sugar": 0.0
      },
      "sourceWaterGrams": 73.9,
      "gramsPerUnit": {},
      "assumption": "껍질·뼈를 뺀 생 닭가슴살의 조리 전 가식부 중량 기준",
      "source": {
        "label": "USDA SR28 · Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "11529",
      "name": "토마토",
      "description": "Tomatoes, red, ripe, raw, year round average",
      "per100g": {
        "kcal": 18.0,
        "carb": 3.89,
        "protein": 0.88,
        "fat": 0.2,
        "fiber": 1.2,
        "water": null,
        "calcium": 10.0,
        "sodium": 5.0,
        "sugar": 2.63
      },
      "sourceWaterGrams": 94.52,
      "gramsPerUnit": {
        "개": 123
      },
      "assumption": "토마토 1개를 중간 크기 123g으로 계산",
      "source": {
        "label": "USDA SR28 · Tomatoes, red, ripe, raw, year round average",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "01116",
      "name": "요거트",
      "description": "Yogurt, plain, whole milk, 8 grams protein per 8 ounce",
      "per100g": {
        "kcal": 61.0,
        "carb": 4.66,
        "protein": 3.47,
        "fat": 3.25,
        "fiber": 0.0,
        "water": null,
        "calcium": 121.0,
        "sodium": 46.0,
        "sugar": 4.66
      },
      "sourceWaterGrams": 87.9,
      "gramsPerUnit": {
        "큰술": 15
      },
      "assumption": "플레인 요거트 1큰술을 15g으로 가정. 무가당 전지유 요거트 참고값",
      "source": {
        "label": "USDA SR28 · Yogurt, plain, whole milk, 8 grams protein per 8 ounce",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "11260",
      "name": "버섯",
      "description": "Mushrooms, white, raw",
      "per100g": {
        "kcal": 22.0,
        "carb": 3.26,
        "protein": 3.09,
        "fat": 0.34,
        "fiber": 1.0,
        "water": null,
        "calcium": 3.0,
        "sodium": 5.0,
        "sugar": 1.98
      },
      "sourceWaterGrams": 92.45,
      "gramsPerUnit": {},
      "assumption": "생 흰 양송이버섯 참고값. 실제 버섯 종류가 다르면 값이 다름",
      "source": {
        "label": "USDA SR28 · Mushrooms, white, raw",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "16123",
      "name": "간장",
      "description": "Soy sauce made from soy and wheat (shoyu)",
      "per100g": {
        "kcal": 53.0,
        "carb": 4.93,
        "protein": 8.14,
        "fat": 0.57,
        "fiber": 0.8,
        "water": null,
        "calcium": 33.0,
        "sodium": 5493.0,
        "sugar": 0.4
      },
      "sourceWaterGrams": 71.15,
      "gramsPerUnit": {
        "작은술": 5.3,
        "큰술": 16
      },
      "assumption": "일반 간장 참고값. 1작은술 5.3g·1큰술 16g, 제품별 나트륨 차이 있음",
      "source": {
        "label": "USDA SR28 · Soy sauce made from soy and wheat (shoyu)",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "11215",
      "name": "다진마늘",
      "description": "Garlic, raw",
      "per100g": {
        "kcal": 149.0,
        "carb": 33.06,
        "protein": 6.36,
        "fat": 0.5,
        "fiber": 2.1,
        "water": null,
        "calcium": 181.0,
        "sodium": 17.0,
        "sugar": 1.0
      },
      "sourceWaterGrams": 58.58,
      "gramsPerUnit": {
        "작은술": 2.8
      },
      "assumption": "생마늘 참고값. 1작은술 2.8g",
      "source": {
        "label": "USDA SR28 · Garlic, raw",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "04044",
      "name": "식용유",
      "description": "Oil, soybean, salad or cooking",
      "per100g": {
        "kcal": 884.0,
        "carb": 0.0,
        "protein": 0.0,
        "fat": 100.0,
        "fiber": 0.0,
        "water": null,
        "calcium": 0.0,
        "sodium": 0.0,
        "sugar": 0.0
      },
      "sourceWaterGrams": 0.0,
      "gramsPerUnit": {
        "작은술": 4.5,
        "큰술": 13.6
      },
      "assumption": "콩기름 참고값. 1작은술 4.5g·1큰술 13.6g, 넣은 기름이 모두 음식에 포함된 것으로 계산",
      "source": {
        "label": "USDA SR28 · Oil, soybean, salad or cooking",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "02047",
      "name": "소금",
      "description": "Salt, table",
      "per100g": {
        "kcal": 0.0,
        "carb": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
        "water": null,
        "calcium": 24.0,
        "sodium": 38758.0,
        "sugar": 0.0
      },
      "sourceWaterGrams": 0.2,
      "gramsPerUnit": {},
      "assumption": "소금 “조금”은 무게 미확인. 나트륨을 0으로 계산하지 않음",
      "source": {
        "label": "USDA SR28 · Salt, table",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "01009",
      "name": "치즈",
      "description": "Cheese, cheddar",
      "per100g": {
        "kcal": 404.0,
        "carb": 3.09,
        "protein": 22.87,
        "fat": 33.31,
        "fiber": 0.0,
        "water": null,
        "calcium": 710.0,
        "sodium": 653.0,
        "sugar": 0.48
      },
      "sourceWaterGrams": 37.02,
      "gramsPerUnit": {},
      "assumption": "체더치즈 참고값. 레시피의 대안 중 계량 가능한 20g 사용; 실제 제품 종류에 따라 다름",
      "source": {
        "label": "USDA SR28 · Cheese, cheddar",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "02030",
      "name": "후추",
      "description": "Spices, pepper, black",
      "per100g": {
        "kcal": 251.0,
        "carb": 63.95,
        "protein": 10.39,
        "fat": 3.26,
        "fiber": 25.3,
        "water": null,
        "calcium": 443.0,
        "sodium": 20.0,
        "sugar": 0.64
      },
      "sourceWaterGrams": 12.46,
      "gramsPerUnit": {},
      "assumption": "흑후추 “조금”은 무게 미확인. 미계량 성분은 전체 영양으로 표시하지 않음",
      "source": {
        "label": "USDA SR28 · Spices, pepper, black",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    },
    {
      "id": "16427",
      "name": "두부",
      "description": "Tofu, raw, regular, prepared with calcium sulfate",
      "per100g": {
        "kcal": 76.0,
        "carb": 1.87,
        "protein": 8.08,
        "fat": 4.78,
        "fiber": 0.3,
        "water": null,
        "calcium": 350.0,
        "sodium": 7.0,
        "sugar": 0.62
      },
      "sourceWaterGrams": 84.55,
      "gramsPerUnit": {},
      "assumption": "일반 칼슘응고 두부 참고값. 제품·응고제에 따라 특히 칼슘 차이가 큼",
      "source": {
        "label": "USDA SR28 · Tofu, raw, regular, prepared with calcium sulfate",
        "url": "https://github.com/alyssaq/usda-sqlite/tree/1e457b599af101ce463a195867574eba16c81acb",
        "release": "USDA SR28 September 2015"
      }
    }
  ],
  "explicitNonMappings": [
    "애호박",
    "된장"
  ]
};
