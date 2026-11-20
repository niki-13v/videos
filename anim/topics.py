"""Topic content. Each topic yields segments (what to show and say) for an episode."""
import random

COLORS = {
    "red": "#e53935", "blue": "#1e88e5", "yellow": "#fdd835", "green": "#43a047",
    "orange": "#fb8c00", "purple": "#8e24aa", "pink": "#ec407a", "brown": "#8d6e63",
}
COLORABLE = [  # (group, kind, noun, plural)
    ("thing", "balloon", "balloon", "balloons"), ("thing", "ball", "ball", "balls"),
    ("thing", "car", "car", "cars"), ("thing", "star", "star", "stars"),
    ("shape", "heart", "heart", "hearts"), ("thing", "cupcake", "cupcake", "cupcakes"),
    ("thing", "flower", "flower", "flowers"), ("thing", "fishc", "fish", "fish"),
]
SHAPES = ["circle", "square", "triangle", "rectangle", "oval", "diamond", "heart", "star"]
FRUITS = [  # kind, name, plural, color hex, color word
    ("apple", "apple", "apples", "#e53935", "red"), ("banana", "banana", "bananas", "#ffe135", "yellow"),
    ("orange", "orange", "oranges", "#fb8c00", "orange"), ("strawberry", "strawberry", "strawberries", "#e53935", "red"),
    ("grapes", "grapes", "grapes", "#8e24aa", "purple"), ("watermelon", "watermelon", "watermelons", "#ef5350", "red and green"),
    ("pear", "pear", "pears", "#c0ca33", "green"), ("cherry", "cherries", "cherries", "#c62828", "red"),
]
ANIMALS = [  # kind, name, sound
    ("cow", "cow", "Moo! Moo!"), ("pig", "pig", "Oink! Oink!"), ("duck", "duck", "Quack! Quack!"),
    ("cat", "cat", "Meow! Meow!"), ("dog", "dog", "Woof! Woof!"), ("sheep", "sheep", "Baa! Baa!"),
    ("chick", "chick", "Cheep! Cheep!"), ("frog", "frog", "Ribbit! Ribbit!"), ("lion", "lion", "Roar!"),
]
COUNTABLE = [("apple", "apples", "#e53935"), ("star", "stars", "#fdd835"), ("ball", "balls", "#1e88e5"),
             ("balloon", "balloons", "#ec407a"), ("flower", "flowers", "#ab47bc"), ("cupcake", "cupcakes", "#f06292"),
             ("strawberry", "strawberries", "#e53935"), ("car", "cars", "#43a047"), ("orange", "oranges", "#fb8c00")]
NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

TOPICS = {
    "colors": dict(title=("Learn", "Colors!"), music="twinkle", playlist="Learn Colors"),
    "shapes": dict(title=("Learn", "Shapes!"), music="london_bridge", playlist="Learn Shapes"),
    "fruits": dict(title=("Yummy", "Fruits!"), music="row_row", playlist="Fruits and Food"),
    "animals": dict(title=("Animal", "Sounds!"), music="old_macdonald", playlist="Animal Sounds"),
    "counting": dict(title=("Count", "to 10!"), music="bouncy", playlist="Counting 1 to 10"),
}


def _ask(item, question, answer_word, answer_color, lines_after):
    steps = [("enter",), ("b", question), ("think", 1.9), ("reveal", answer_word, answer_color)]
    steps += [("b", answer_word.capitalize() + "!", 0.95)]
    steps += [("b", line) for line in lines_after]
    steps += [("exit",)]
    return dict(item=item, steps=steps, chapter=answer_word.capitalize())


def segments(topic, rnd: random.Random, n=None):
    if topic == "colors":
        names = list(COLORS)
        rnd.shuffle(names)
        out = []
        for c in names[: n or 8]:
            g, kind, noun, _ = rnd.choice(COLORABLE)
            item = dict(group=g, kind=kind, color=COLORS[c], noun=noun)
            out.append(_ask(item, f"What color is this {noun}?", c, COLORS[c], [f"It's a {c} {noun}!", f"{c.capitalize()}!"]))
        return out
    if topic == "shapes":
        shp = SHAPES[:]
        rnd.shuffle(shp)
        out = []
        for sname in shp[: n or 8]:
            cname = rnd.choice(list(COLORS))
            item = dict(group="shape", kind=sname, color=COLORS[cname], noun=sname)
            out.append(_ask(item, "What shape is this?", sname, COLORS[cname], [f"It's a {cname} {sname}!", f"{sname.capitalize()}!"]))
        return out
    if topic == "fruits":
        fr = FRUITS[:]
        rnd.shuffle(fr)
        out = []
        for kind, name, plural, col, cword in fr[: n or 8]:
            g = "thing"
            item = dict(group=g, kind=kind, color=col, noun=name)
            out.append(_ask(item, "What fruit is this?", name, col, [f"{plural.capitalize()} are {cword}!", "Yum yum yum!"]))
        return out
    if topic == "animals":
        an = ANIMALS[:]
        rnd.shuffle(an)
        out = []
        for kind, name, sound in an[: n or 7]:
            item = dict(group="animal", kind=kind, color="#ffffff", noun=name)
            steps = [("enter",), ("b", "Who is this?"), ("think", 1.6), ("reveal", name, "#ff7043"),
                     ("b", f"It's a {name}!"), ("b", f"What does the {name} say?"), ("think", 1.6),
                     ("reveal", sound.split("!")[0] + "!", "#ff7043"), ("i", sound), ("b", f"The {name} says {sound.split('!')[0].lower()}!"),
                     ("exit",)]
            out.append(dict(item=item, steps=steps, chapter=name.capitalize()))
        return out
    if topic == "counting":
        top = n or 10
        out = []
        for k in range(1, top + 1):
            kind, plural, col = rnd.choice(COUNTABLE)
            group = "thing"
            item = dict(group=group, kind=kind, color=col, noun=plural)
            word = NUMBERS[k]
            noun = plural if k > 1 else ({"strawberries": "strawberry", "cherries": "cherry"}.get(plural, plural[:-1]))
            steps = [("b", f"How many {plural}?" if k > 1 else f"Let's count!")]
            steps += [("count", k)]
            steps += [("reveal", str(k), col), ("b", f"{word.capitalize()} {noun}!"), ("exit",)]
            out.append(dict(item=item, steps=steps, chapter=f"Number {k}", count=k))
        return out
    raise ValueError(topic)


def metadata(topic, segs, chapters, rnd):
    names = [s["chapter"] for s in segs]
    sample = ", ".join(names[:3])
    titles = {
        "colors": f"Learn Colors with Bramble 🎈 {sample} & More | Colors for Toddlers",
        "shapes": f"Learn Shapes with Bramble 🔺 {sample} & More | Shapes for Toddlers",
        "fruits": f"Yummy Fruits with Bramble 🍓 {sample} & More | Learn Fruit Names for Kids",
        "animals": f"Animal Sounds with Bramble 🐮 {sample} & More | Farm Animals for Toddlers",
        "counting": "Count to 10 with Bramble 🔢 Learn Numbers 1 to 10 | Counting for Toddlers",
    }
    learn = {
        "colors": "colors", "shapes": "shapes", "fruits": "fruit names and their colors",
        "animals": "animals and the sounds they make", "counting": "how to count from 1 to 10",
    }[topic]
    chap = "\n".join(f"{int(t // 60)}:{int(t % 60):02d} {name}" for t, name in chapters)
    desc = (
        f"Learn {learn} with Bramble the bear! 🐻\n\n"
        f"Bramble asks a question, waits for your little one to answer, then shows the answer "
        f"with big words, bright colors and fun sounds. Perfect for toddlers and preschoolers (ages 1-5).\n\n"
        f"In this video:\n{chap}\n\n"
        f"Subscribe for new learning videos with Bramble and friends every day!\n\n"
        f"#toddlerlearning #kidslearning #{topic}forkids #preschool #bramble"
    )
    tags = {
        "colors": ["learn colors", "colors for toddlers", "colors for kids", "color names", "learning colors"],
        "shapes": ["learn shapes", "shapes for toddlers", "shapes for kids", "shape names", "learning shapes"],
        "fruits": ["fruit names", "learn fruits", "fruits for toddlers", "fruits for kids", "healthy food for kids"],
        "animals": ["animal sounds", "farm animals", "animal sounds for kids", "animal names", "old macdonald"],
        "counting": ["count to 10", "counting for kids", "numbers 1 to 10", "learn numbers", "123 for toddlers"],
    }[topic] + ["toddler learning video", "preschool learning", "educational videos for toddlers", "kids learning videos", "bramble the bear", "first words"]
    return titles[topic][:100], desc, tags


def find_segments(topic, rnd: random.Random, n=6):
    """Round 2 game: three items on screen, find the right one."""
    out = []
    for _ in range(n if topic != "counting" else 0):
        if topic == "colors":
            cols = rnd.sample(list(COLORS), 3)
            items = []
            for c in cols:
                g, kind, noun, _ = rnd.choice(COLORABLE)
                items.append(dict(group=g, kind=kind, color=COLORS[c], noun=noun, word=c))
            j = rnd.randrange(3)
            q, word = f"Can you find something {cols[j]}?", cols[j]
            lines = [f"Here it is! A {cols[j]} {items[j]['noun']}!"]
        elif topic == "shapes":
            shp = rnd.sample(SHAPES, 3)
            items = [dict(group="shape", kind=s, color=COLORS[rnd.choice(list(COLORS))], noun=s, word=s) for s in shp]
            j = rnd.randrange(3)
            q, word, lines = f"Can you find the {shp[j]}?", shp[j], [f"Here it is! The {shp[j]}!"]
        elif topic == "fruits":
            fr = rnd.sample(FRUITS, 3)
            items = [dict(group="thing", kind=k, color=c, noun=nm, word=nm) for k, nm, _, c, _ in fr]
            j = rnd.randrange(3)
            q, word, lines = f"Can you find the {fr[j][1]}?", fr[j][1], [f"Here it is! Yummy {fr[j][1]}!"]
        elif topic == "animals":
            an = rnd.sample(ANIMALS, 3)
            items = [dict(group="animal", kind=k, color="#ffffff", noun=nm, word=nm) for k, nm, _ in an]
            j = rnd.randrange(3)
            snd = an[j][2].split("!")[0].lower()
            q, word = f"Who says {snd}?", an[j][1]
            lines = [f"The {an[j][1]}!", ("i", an[j][2])]
        col = items[j]["color"] if items[j]["group"] != "animal" else "#ff7043"
        steps = [("enter",), ("b", q), ("think", 2.0), ("pick", word, col)]
        steps += [st if isinstance(st, tuple) else ("b", st) for st in lines]
        steps += [("exit",)]
        out.append(dict(items=items, target=j, steps=steps, chapter=f"Find the {word}"))
    return out
