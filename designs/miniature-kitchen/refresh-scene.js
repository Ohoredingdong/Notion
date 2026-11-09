/* Measured artwork registration. Display projection never rewrites saved item coordinates. */
window.KitchenSceneProjection=Object.freeze({
  "version": 1,
  "world": [
    1254,
    893
  ],
  "stage": [
    308,
    32,
    640,
    790
  ],
  "base": [
    308,
    814,
    640,
    8
  ],
  "panels": {
    "freshLeft": {
      "body": [
        308,
        32,
        320,
        471
      ],
      "open": [
        156,
        24,
        176,
        480
      ],
      "polygon": [
        [
          158,
          26
        ],
        [
          191,
          26
        ],
        [
          328,
          63
        ],
        [
          328,
          480
        ],
        [
          190,
          498
        ],
        [
          157,
          495
        ]
      ],
      "interior": [
        332,
        72,
        280,
        397
      ],
      "shelves": [
        242,
        348,
        447
      ],
      "capacity": 160,
      "cargo": [
        239,
        80,
        80,
        340
      ],
      "cargoFloors": [
        242,
        392
      ]
    },
    "freshRight": {
      "body": [
        628,
        32,
        320,
        471
      ],
      "open": [
        924,
        24,
        184,
        480
      ],
      "polygon": [
        [
          924,
          62
        ],
        [
          1074,
          26
        ],
        [
          1104,
          24
        ],
        [
          1104,
          497
        ],
        [
          1078,
          501
        ],
        [
          924,
          480
        ]
      ],
      "interior": [
        648,
        72,
        276,
        397
      ],
      "shelves": [
        242,
        348,
        447
      ],
      "capacity": 160,
      "cargo": [
        937,
        80,
        80,
        340
      ],
      "cargoFloors": [
        242,
        392
      ]
    },
    "frozenLeft": {
      "body": [
        308,
        503,
        320,
        311
      ],
      "open": [
        156,
        500,
        176,
        346
      ],
      "polygon": [
        [
          157,
          514
        ],
        [
          190,
          513
        ],
        [
          328,
          501
        ],
        [
          328,
          792
        ],
        [
          188,
          844
        ],
        [
          157,
          838
        ]
      ],
      "interior": [
        334,
        520,
        278,
        254
      ],
      "shelves": [
        640,
        748
      ],
      "capacity": 100,
      "cargo": [
        239,
        530,
        80,
        270
      ],
      "cargoFloors": [
        790
      ]
    },
    "frozenRight": {
      "body": [
        628,
        503,
        320,
        311
      ],
      "open": [
        924,
        500,
        184,
        346
      ],
      "polygon": [
        [
          924,
          501
        ],
        [
          1074,
          513
        ],
        [
          1103,
          518
        ],
        [
          1104,
          839
        ],
        [
          1076,
          844
        ],
        [
          924,
          792
        ]
      ],
      "interior": [
        650,
        520,
        274,
        254
      ],
      "shelves": [
        640,
        748
      ],
      "capacity": 100,
      "cargo": [
        937,
        530,
        80,
        270
      ],
      "cargoFloors": [
        790
      ]
    }
  },
  "hinges": {
    "freshLeft": {
      "box": [
        285,
        24,
        55,
        37
      ],
      "corner_radius": 5,
      "visible_when": "freshLeft open"
    },
    "freshRight": {
      "box": [
        915,
        23,
        56,
        37
      ],
      "corner_radius": 5,
      "visible_when": "freshRight open"
    },
    "center": {
      "box": [
        597,
        31,
        57,
        27
      ],
      "corner_radius": 3,
      "visible_when": "At least one upper door open; main quarter clips already retain matching center halves"
    }
  },
  "foodSize": [
    1254,
    1254
  ],
  "foodBoxes": {
    "계란": [
      22,
      198,
      235,
      137
    ],
    "토마토": [
      283,
      172,
      203,
      169
    ],
    "두부": [
      515,
      206,
      227,
      132
    ],
    "브로콜리": [
      775,
      141,
      197,
      198
    ],
    "우유": [
      1042,
      102,
      169,
      233
    ],
    "대파": [
      19,
      471,
      243,
      134
    ],
    "양송이버섯": [
      301,
      435,
      180,
      179
    ],
    "김치": [
      529,
      419,
      201,
      196
    ],
    "소고기": [
      764,
      487,
      217,
      116
    ],
    "생선": [
      1011,
      484,
      219,
      123
    ],
    "새우": [
      28,
      759,
      226,
      126
    ],
    "만두": [
      275,
      758,
      221,
      125
    ],
    "냉동 채소": [
      519,
      760,
      224,
      119
    ],
    "간장": [
      828,
      667,
      106,
      224
    ],
    "고추장": [
      1040,
      710,
      177,
      184
    ],
    "된장": [
      61,
      990,
      179,
      189
    ],
    "소금": [
      313,
      991,
      162,
      187
    ]
  },
  "closed": {
    "size": [
      1486,
      1058
    ],
    "scale": 0.8780487804878049,
    "center": 742,
    "sourceTop": 56,
    "top": 1,
    "faces": {
      "freshLeft": [
        386,
        56,
        354,
        533
      ],
      "freshRight": [
        744,
        56,
        354,
        533
      ],
      "frozenLeft": [
        386,
        592,
        354,
        354
      ],
      "frozenRight": [
        744,
        592,
        354,
        354
      ]
    }
  },
  "room": {
    "size": [
      1254,
      671
    ],
    "fridge": [
      250,
      27,
      490,
      604.84375
    ],
    "counter": [
      830,
      332,
      388,
      8
    ],
    "floor": 632
  }
});
