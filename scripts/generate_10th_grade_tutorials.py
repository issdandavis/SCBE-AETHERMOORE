#!/usr/bin/env python3
"""
Generate 10th-grade tutorial responses for SCBE codex skill stubs.
Reads stubs, fills in responses, strips skill_content/sample_packets, writes output JSONL.
"""
import json
import re
import sys
import os

INPUT = r"C:\Users\issda\SCBE-AETHERMOORE\training-data\sft\codex_skill_tutorials_10th_grade_stubs.jsonl"
OUTPUT = r"C:\Users\issda\SCBE-AETHERMOORE\training-data\sft\codex_skill_tutorials_10th_grade.jsonl"


def clean_skill_name(source: str) -> str:
    """Convert kebab-case skill source to readable name."""
    return source.replace("-", " ").replace("_", " ").title()


def extract_key_concepts(skill_content: str) -> list[str]:
    """Pull out key concepts from skill content for response generation."""
    concepts = []
    # Extract headers
    for m in re.finditer(r"^##\s+(.+)$", skill_content, re.MULTILINE):
        concepts.append(m.group(1).strip())
    # Extract bullet points
    for m in re.finditer(r"^[-*]\s+(.+)$", skill_content, re.MULTILINE):
        line = m.group(1).strip()
        if len(line) > 10 and not line.startswith("`"):
            concepts.append(line)
    return concepts[:8]


def extract_use_cases(skill_content: str) -> list[str]:
    """Extract use cases from skill content."""
    cases = []
    in_use_cases = False
    for line in skill_content.split("\n"):
        if "use case" in line.lower() or "when to use" in line.lower() or "typical request" in line.lower():
            in_use_cases = True
            continue
        if in_use_cases and line.strip().startswith(("-", "*")):
            cases.append(line.strip().lstrip("-* "))
        elif in_use_cases and line.strip().startswith("#"):
            in_use_cases = False
    return cases[:5]


def extract_steps(skill_content: str) -> list[str]:
    """Extract workflow steps."""
    steps = []
    for m in re.finditer(r"^\d+\.\s+(.+)$", skill_content, re.MULTILINE):
        steps.append(m.group(1).strip())
    if not steps:
        for m in re.finditer(r"^###\s+[A-Z]\.\s+(.+)$", skill_content, re.MULTILINE):
            steps.append(m.group(1).strip())
    return steps[:6]


def get_category_analogy(category: str) -> dict:
    """Return analogy domains per category."""
    analogies = {
        "infrastructure": {
            "domain": "school IT lab",
            "examples": ["setting up a computer lab", "rebooting the school Wi-Fi", "getting a new phone ready for class"],
        },
        "browser": {
            "domain": "library research",
            "examples": ["looking up a book in the library catalog", "using the school database for a research paper", "browsing the internet for a project"],
        },
        "ai_coordination": {
            "domain": "group project",
            "examples": ["passing notes in class", "a relay race where runners hand off the baton", "a group chat where everyone updates their progress"],
        },
        "security": {
            "domain": "school safety",
            "examples": ["checking student IDs at the door", "a hall pass system", "locking your locker combination"],
        },
        "training": {
            "domain": "studying for a test",
            "examples": ["making flashcards", "a study guide", "practice tests before the real exam"],
        },
        "publishing": {
            "domain": "school newspaper",
            "examples": ["submitting an article to the school paper", "posting on the school bulletin board", "publishing a yearbook"],
        },
        "governance": {
            "domain": "student council rules",
            "examples": ["the student council voting on a new rule", "a referee making a call in a game", "classroom rules everyone agrees to follow"],
        },
        "data": {
            "domain": "organizing your binder",
            "examples": ["sorting papers into folders", "organizing your notes by subject", "keeping a planner updated"],
        },
        "general": {
            "domain": "everyday school life",
            "examples": ["managing your homework schedule", "coordinating a group project", "keeping track of your assignments"],
        },
        "game": {
            "domain": "video games",
            "examples": ["leveling up in an RPG", "managing inventory in Minecraft", "unlocking achievements"],
        },
        "creative": {
            "domain": "art class",
            "examples": ["working on a group mural", "editing a video for class", "writing a collaborative story"],
        },
    }
    return analogies.get(category, analogies["general"])


def generate_what_is_response(record: dict) -> str:
    """Generate 'What is X' style response."""
    name = clean_skill_name(record.get("skill_source", ""))
    desc = record.get("skill_description", "")
    content = record.get("skill_content", "") or ""
    sample = record.get("sample_packets", "") or ""
    category = record.get("category", "general")
    analogy = get_category_analogy(category)
    concepts = extract_key_concepts(content)
    use_cases = extract_use_cases(content)

    # Build response based on what we have
    response_parts = []

    # Opening - what is it
    if "arxiv" in name.lower():
        response_parts.append(
            f"{name} is a tool that helps AI agents find and read scientific research papers on arXiv, which is like a giant online library for academic papers. "
            f"Think of it like {analogy['examples'][0]} -- except instead of a person flipping through pages, an AI agent does it automatically."
        )
    elif "phone" in name.lower() or "emulator" in name.lower():
        response_parts.append(
            f"{name} is a set of tools for running a virtual phone on your computer. "
            f"Imagine you could have a fake Android phone running right on your desktop -- that is what an emulator does. "
            f"This skill helps you start it up, fix it when it freezes, and connect it to the rest of the system. "
            f"Think of it like {analogy['examples'][0]}."
        )
    elif "cross-talk" in record.get("skill_source", "") or "communication" in name.lower() or "crosstalk" in record.get("source_type", ""):
        response_parts.append(
            f"{name} is about how AI agents send messages to each other so they can work together without stepping on each other's toes. "
            f"Think of it like {analogy['examples'][0]}. "
            f"When you are working on a group project, you need to tell your teammates what you finished, what you are stuck on, and what they should do next. AI agents need the same thing."
        )
    elif "governance" in name.lower() or "gate" in name.lower():
        response_parts.append(
            f"{name} is a safety checkpoint system for AI agents. "
            f"Think of it like {analogy['examples'][0]}. "
            f"Before an AI agent can do something important, it has to pass through a gate that checks whether the action is safe, appropriate, and follows the rules."
        )
    elif "training" in name.lower() or "sft" in name.lower():
        response_parts.append(
            f"{name} is about teaching AI models to get better at their jobs. "
            f"Think of it like {analogy['examples'][0]}. "
            f"Just like you study to improve your grades, AI models need practice data to learn how to respond correctly."
        )
    elif "publish" in name.lower() or "content" in name.lower():
        response_parts.append(
            f"{name} handles getting content out into the world across different platforms. "
            f"Think of it like {analogy['examples'][0]}. "
            f"When you write something good, you want people to see it -- this tool helps post content to multiple places at once while making sure everything follows the rules."
        )
    elif "security" in name.lower() or "audit" in name.lower() or "antivirus" in name.lower():
        response_parts.append(
            f"{name} is a security tool that protects the system from threats. "
            f"Think of it like {analogy['examples'][0]}. "
            f"Just like your school has security measures to keep everyone safe, this tool checks for vulnerabilities and blocks anything suspicious."
        )
    elif "browser" in name.lower() or "web" in name.lower():
        response_parts.append(
            f"{name} helps AI agents browse the internet safely and efficiently. "
            f"Think of it like {analogy['examples'][0]}. "
            f"Instead of a person clicking through websites, an AI agent navigates web pages, extracts useful information, and brings it back in an organized format."
        )
    elif "deploy" in name.lower() or "fleet" in name.lower():
        response_parts.append(
            f"{name} handles sending trained AI models out into the real world where they can actually be used. "
            f"Think of it like a coach deciding which players go into the game. "
            f"The tool checks that each model is ready, then puts it where it needs to be."
        )
    elif "shopify" in name.lower() or "store" in name.lower() or "revenue" in name.lower():
        response_parts.append(
            f"{name} connects the AI system to online stores and revenue tracking. "
            f"Think of it like running a school fundraiser -- you need to manage products, track sales, and make sure everything adds up. "
            f"This tool automates the business side of things."
        )
    elif "youtube" in name.lower() or "video" in name.lower():
        response_parts.append(
            f"{name} manages YouTube video content -- titles, descriptions, tags, and scheduling. "
            f"Think of it like being the editor of your school's YouTube channel. "
            f"You need to make sure every video has a good title, the right description, and proper tags so people can find it."
        )
    elif "notion" in name.lower() or "obsidian" in name.lower():
        response_parts.append(
            f"{name} connects the system to note-taking and knowledge management tools. "
            f"Think of it like having a super-organized digital binder that automatically sorts your notes, links related topics together, and makes everything searchable."
        )
    elif "discord" in name.lower() or "slack" in name.lower() or "social" in name.lower() or "twitter" in name.lower():
        response_parts.append(
            f"{name} manages social media and community interactions. "
            f"Think of it like being the social media manager for your school club. "
            f"You post updates, respond to messages, and keep the community engaged -- but this tool does it across multiple platforms at once."
        )
    elif "sacred" in name.lower() or "tongue" in name.lower() or "egg" in name.lower():
        response_parts.append(
            f"{name} is part of the system's special language and identity framework. "
            f"Think of it like a secret code that your friend group uses. "
            f"The system has six special 'languages' (called Sacred Tongues) that encode information in different ways, making data more secure and meaningful."
        )
    elif "manifold" in name.lower() or "geometry" in name.lower() or "hyperbolic" in name.lower():
        response_parts.append(
            f"{name} uses advanced math to measure how safe or risky an AI action is. "
            f"Think of it like a video game map where the further you go from the safe zone, the harder the enemies get -- exponentially harder. "
            f"This math makes it so that bad actors would need impossibly huge amounts of computing power to cause harm."
        )
    elif "story" in name.lower() or "lore" in name.lower() or "canon" in name.lower() or "book" in name.lower() or "manuscript" in name.lower():
        response_parts.append(
            f"{name} helps create and manage story content that stays consistent with the project's world-building. "
            f"Think of it like being the continuity editor for a TV show -- making sure characters act consistently and plot details do not contradict each other across episodes."
        )
    elif "colab" in name.lower() or "compute" in name.lower():
        response_parts.append(
            f"{name} manages cloud computing resources for training AI models. "
            f"Think of it like borrowing the school's fancy computer lab when you need extra processing power. "
            f"Instead of running everything on your own machine, you can use powerful remote computers to do heavy work."
        )
    elif "session" in name.lower() or "analytics" in name.lower() or "sitrep" in name.lower():
        response_parts.append(
            f"{name} tracks what AI agents have been doing and how resources are being used. "
            f"Think of it like checking your screen time on your phone -- it tells you how long you spent, what you did, and how much it cost."
        )
    elif "disk" in name.lower() or "storage" in name.lower():
        response_parts.append(
            f"{name} helps manage storage space on the computer. "
            f"Think of it like cleaning out your locker at school -- finding old papers you do not need, organizing what you want to keep, and making room for new stuff."
        )
    elif "state" in name.lower() or "9d" in name.lower() or "entropy" in name.lower():
        response_parts.append(
            f"{name} tracks the current condition of the AI system across multiple dimensions. "
            f"Think of it like a health bar in a video game, except instead of just one bar, you have nine different stats (like strength, speed, defense) that all work together to determine what the AI can and should do."
        )
    elif "patch" in name.lower() or "diff" in name.lower():
        response_parts.append(
            f"{name} helps visualize and manage changes to code. "
            f"Think of it like using 'track changes' in a Google Doc -- you can see exactly what was added, removed, or modified before accepting the changes."
        )
    elif "pdf" in name.lower() or "doc" in name.lower():
        response_parts.append(
            f"{name} creates and manages documents and reports. "
            f"Think of it like having a really smart printer that can also merge, split, and edit documents automatically."
        )
    elif "email" in name.lower():
        response_parts.append(
            f"{name} checks and manages email across different accounts. "
            f"Think of it like having a personal assistant who checks your inbox, flags the important messages, and gives you a summary so you do not miss anything."
        )
    elif "pitch" in name.lower() or "investor" in name.lower():
        response_parts.append(
            f"{name} helps prepare presentations and outreach to potential investors or partners. "
            f"Think of it like preparing for a Shark Tank pitch at school -- you need to organize your idea, know your audience, and present it convincingly."
        )
    elif "git" in name.lower() or "release" in name.lower() or "dual forge" in name.lower():
        response_parts.append(
            f"{name} manages code versions and releases across platforms like GitHub. "
            f"Think of it like keeping a journal where every entry is dated and you can always go back to any previous version. "
            f"When you are ready to share your work with the world, this tool packages it up properly."
        )
    elif "ide" in name.lower() or "copilot" in name.lower():
        response_parts.append(
            f"{name} provides intelligent coding assistance within the development environment. "
            f"Think of it like having a really smart tutor looking over your shoulder while you write code, catching mistakes and suggesting improvements."
        )
    elif "n8n" in name.lower() or "workflow" in name.lower():
        response_parts.append(
            f"{name} automates multi-step workflows by connecting different tools together. "
            f"Think of it like a Rube Goldberg machine where one action triggers the next -- except instead of dominoes and marbles, it is connecting web services, databases, and AI agents."
        )
    elif "flock" in name.lower() or "swarm" in name.lower() or "fleet" in name.lower():
        response_parts.append(
            f"{name} coordinates multiple AI agents working together. "
            f"Think of it like coaching a basketball team -- each player has a role (point guard, center, shooting guard), and the coach makes sure everyone is in the right position and communicating."
        )
    elif "mobile" in name.lower() or "connector" in name.lower():
        response_parts.append(
            f"{name} connects the AI system to external services like Shopify, Slack, or Notion. "
            f"Think of it like having adapters that let you plug different chargers into the same outlet -- each service speaks a different language, and this tool translates between them."
        )
    elif "personal" in name.lower() or "rag" in name.lower():
        response_parts.append(
            f"{name} is a fast-recall knowledge base that stores important facts about the project. "
            f"Think of it like a cheat sheet you keep in your pocket -- instead of searching through hundreds of files, you can quickly look up the answer."
        )
    elif "longform" in name.lower():
        response_parts.append(
            f"{name} manages long-running tasks that take many steps to complete. "
            f"Think of it like a multi-day school project -- you save your progress, leave notes about where you stopped, and pick up right where you left off next time."
        )
    elif "transcri" in name.lower() or "audio" in name.lower():
        response_parts.append(
            f"{name} converts audio into text or works with sound data. "
            f"Think of it like those auto-generated captions on YouTube videos -- the system listens to audio and writes down what it hears."
        )
    elif "art" in name.lower() or "image" in name.lower() or "visual" in name.lower():
        response_parts.append(
            f"{name} generates visual content like illustrations, character art, and diagrams. "
            f"Think of it like having a digital art assistant that can draw what you describe -- characters, scenes, diagrams, whatever you need."
        )
    elif "research" in name.lower():
        response_parts.append(
            f"{name} runs structured research across the internet and academic sources. "
            f"Think of it like having a research assistant who checks multiple sources, verifies facts, and organizes everything with dates and confidence scores."
        )
    elif "skill" in name.lower() and "creat" in name.lower():
        response_parts.append(
            f"{name} helps create new capabilities for the AI system. "
            f"Think of it like writing a recipe -- you define the ingredients (inputs), the steps (workflow), and what the dish should look like when it is done (output)."
        )
    elif "context" in name.lower() and "catalog" in name.lower():
        response_parts.append(
            f"{name} maps different types of tasks to the right tools and resources. "
            f"Think of it like a school class schedule that tells you which room, teacher, and supplies you need for each subject."
        )
    elif "credit" in name.lower() or "ledger" in name.lower():
        response_parts.append(
            f"{name} tracks computing resources and credits like a digital bank account. "
            f"Think of it like tracking your lunch money balance -- every time an AI agent does work, it costs credits, and this system keeps the books balanced."
        )
    elif "webtoon" in name.lower() or "manhwa" in name.lower() or "comic" in name.lower() or "storyboard" in name.lower():
        response_parts.append(
            f"{name} adapts stories into visual comic or webtoon format. "
            f"Think of it like turning a book you love into a graphic novel -- you need to decide which scenes get panels, how to frame the action, and how the story flows visually."
        )
    elif "tuxemon" in name.lower() or "game" in name.lower():
        response_parts.append(
            f"{name} works with game development and modification. "
            f"Think of it like modding your favorite video game -- adding new creatures, maps, or features to make the game your own."
        )
    else:
        response_parts.append(
            f"{name} is a specialized tool in the SCBE-AETHERMOORE system. "
            f"Think of it like {analogy['examples'][0]}. "
            f"{desc}"
        )

    # Middle - what it does specifically
    if concepts:
        key = concepts[:3]
        response_parts.append(
            f"\n\nHere is what it actually handles: {', '.join(c.lower() for c in key)}. "
        )
    elif desc:
        response_parts.append(f"\n\n{desc} ")

    # Why it matters
    response_parts.append(
        "\n\nWhy does this matter for AI safety? In the SCBE system, AI agents do not just run wild doing whatever they want. "
        "Every action goes through checks and balances, kind of like how a school has rules, teachers, and a principal to make sure things run smoothly. "
        f"This particular tool is one piece of that bigger puzzle, making sure the '{category}' side of things stays organized and safe."
    )

    return "".join(response_parts)


def generate_step_by_step_response(record: dict) -> str:
    """Generate step-by-step walkthrough with analogy."""
    name = clean_skill_name(record.get("skill_source", ""))
    content = record.get("skill_content", "") or ""
    sample = record.get("sample_packets", "") or ""
    category = record.get("category", "general")
    analogy = get_category_analogy(category)
    steps = extract_steps(content)
    concepts = extract_key_concepts(content)

    response_parts = []

    # Analogy opener
    if "phone" in name.lower() or "emulator" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like setting up a new phone for the first time."
        )
        step_analogies = [
            ("Check if the phone is already on", "First, the system checks if the virtual phone is already running. No point turning on a phone that is already on."),
            ("Fix it if it is stuck", "If the phone froze or crashed, you force-restart it. The system clears out stale lock files and restarts the emulator."),
            ("Boot it up", "Now you actually start the virtual phone. You can customize the screen size and font, just like adjusting settings on a real phone."),
            ("Open your apps", "Once the phone is running, you navigate to the apps you need -- in this case, Polly Pad and the chat interface."),
            ("Use it", "Now the AI agent can interact with the phone just like you would -- tapping, typing, and browsing."),
        ]
    elif "arxiv" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like doing research at a library."
        )
        step_analogies = [
            ("Walk into the library", "First, the system opens up a browser lane dedicated to research, kind of like walking into the research section of the library."),
            ("Search the catalog", "Next, it searches arXiv for papers on your topic. ArXiv is like a massive digital library with millions of science papers."),
            ("Pull the book off the shelf", "The system opens the paper's abstract page to read the summary, title, authors, and categories -- like reading the back cover of a book."),
            ("Take notes", "Finally, it saves everything it found into a structured file so other parts of the system can use it later. Like writing notes on index cards."),
        ]
    elif "cross-talk" in record.get("skill_source", "") or "communication" in name.lower() or "crosstalk" in record.get("source_type", ""):
        response_parts.append(
            f"Let me walk you through {name} like passing notes in a group project."
        )
        step_analogies = [
            ("Write your note", "An AI agent creates a message packet with what it did, what is blocking it, and what should happen next. Like writing 'I finished the intro paragraph, need someone to do the body.'"),
            ("Label the note", "The message gets a unique ID, a timestamp, and labels for who sent it and who should read it. Like putting your name and the date on your note."),
            ("Put it in the shared folder", "The packet goes into a shared location where other agents can find it. Think of dropping your note into a shared Google Drive folder."),
            ("Other agents read and respond", "The receiving agent picks up the packet, does its part, and writes its own note back. The cycle continues until the task is done."),
        ]
    elif "governance" in name.lower() or "gate" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like going through school security."
        )
        step_analogies = [
            ("Approach the gate", "An AI agent wants to do something -- maybe send a message or access data. First it has to approach the governance checkpoint."),
            ("Show your ID", "The system checks the agent's identity, what it is trying to do, and whether it has permission. Like showing your student ID at the school entrance."),
            ("Get scanned", "The request gets evaluated against safety rules. Is this action risky? Does it follow the guidelines? This is like walking through a metal detector."),
            ("Get a verdict", "The gate gives one of four answers: ALLOW (go ahead), QUARANTINE (hold on, need review), ESCALATE (talk to the principal), or DENY (absolutely not)."),
        ]
    elif "training" in name.lower() or "sft" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like studying for a big exam."
        )
        step_analogies = [
            ("Gather your study materials", "First, you collect all the data the AI needs to learn from -- questions, answers, examples. Like gathering your textbook, notes, and practice problems."),
            ("Organize by topic", "The data gets sorted and validated. Bad data gets filtered out. Like sorting your notes by chapter and throwing away the ones with wrong info."),
            ("Do the practice problems", "The AI model trains on the data, learning patterns and improving. Like actually sitting down and working through practice problems."),
            ("Check your score", "After training, you test the model to see if it improved. Like taking a practice quiz to see if your studying paid off."),
        ]
    elif "publish" in name.lower() or "content" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like publishing the school newspaper."
        )
        step_analogies = [
            ("Write your article", "First, the content gets created or queued up -- an article, a social post, or a dataset description."),
            ("Editorial review", "Before publishing, the content goes through a governance check. Is it accurate? Does it follow guidelines? Like an editor reviewing your article."),
            ("Format for each platform", "The same content might go to Twitter, LinkedIn, GitHub, and more. Each platform needs different formatting. Like reformatting an article for the website vs. the printed paper."),
            ("Hit publish", "Finally, the content goes live on all platforms. The system tracks what was published where and when."),
        ]
    elif "security" in name.lower() or "audit" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like a school safety drill."
        )
        step_analogies = [
            ("Check the perimeter", "First, the system scans for exposed secrets, weak passwords, and open vulnerabilities. Like checking that all doors and windows are locked."),
            ("Test the alarms", "It runs automated tests to make sure security measures are actually working. Like testing the fire alarm to make sure it goes off."),
            ("Write the report", "Everything gets documented -- what passed, what failed, and what needs fixing. Like the safety report the principal gets after a drill."),
            ("Fix what is broken", "Any issues found get flagged for immediate action. Critical problems get escalated, just like a real safety hazard gets reported right away."),
        ]
    elif "youtube" in name.lower() or "video" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like managing a school YouTube channel."
        )
        step_analogies = [
            ("Plan your updates", "First, you create a plan for what needs to change -- new titles, better descriptions, updated tags. Like making a list of edits before touching anything."),
            ("Preview the changes", "Before anything goes live, you preview what the changes will look like. Like proofreading before posting."),
            ("Apply the changes", "Once you are happy with the preview, the tool pushes the updates to YouTube. Like hitting 'save' on your edits."),
            ("Check the results", "Finally, you review the scores and analytics to see if the changes helped. Like checking your view count the next day."),
        ]
    elif "browser" in name.lower() or "web" in name.lower() or "swarm" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like organizing a research team at the library."
        )
        step_analogies = [
            ("Assign the task", "First, you tell the AI browser agent what you need -- search this, navigate there, extract that. Like giving each team member a specific research question."),
            ("Navigate to the source", "The agent opens a browser and goes to the right website. Like walking to the right section of the library."),
            ("Extract the information", "It reads the page, grabs the relevant data, and structures it neatly. Like taking organized notes from a textbook."),
            ("Bring it back safely", "The data comes back through safety checks to make sure nothing malicious snuck in. Like a librarian checking your sources are legitimate."),
        ]
    elif "sacred" in name.lower() or "tongue" in name.lower() or "egg" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like a secret language club at school."
        )
        step_analogies = [
            ("Choose your language", "The system has six special encoding languages called Sacred Tongues. Each one processes information differently, like how different subjects use different notation (math uses numbers, music uses notes)."),
            ("Encode the message", "Your data gets transformed through the chosen tongue. Each tongue adds a different weight and perspective to the information."),
            ("Layer the protection", "Multiple tongues can be combined for stronger encoding. Like encrypting a message, then putting it in a locked box, then hiding the box."),
            ("Verify identity", "Sacred Eggs serve as identity tokens -- like digital birth certificates that prove who created what and when."),
        ]
    elif "colab" in name.lower() or "compute" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like borrowing the computer lab for a big project."
        )
        step_analogies = [
            ("Reserve the lab", "First, the system claims a cloud computing session. Like signing up for computer lab time."),
            ("Set up your workspace", "It uploads the right notebooks and data to the cloud machine. Like loading your project files onto the lab computers."),
            ("Run the heavy work", "The cloud machine does the computationally expensive training. Like using the lab's powerful computers instead of your slow laptop."),
            ("Save and return", "When done, results are saved and the session is released for others. Like saving your work to a USB drive and logging off."),
        ]
    elif "deploy" in name.lower() or "fleet" in name.lower():
        response_parts.append(
            f"Let me walk you through {name} like getting a school team ready for a tournament."
        )
        step_analogies = [
            ("Check who is ready", "First, you verify each model passed its quality checks. Like making sure every player passed their physical and academic requirements."),
            ("Assign positions", "Each model gets deployed to the right server or service. Like putting each player in their best position."),
            ("Go live", "The models start serving real requests. Like the team taking the field for the actual game."),
            ("Monitor performance", "You watch how everything performs and can roll back if something goes wrong. Like a coach pulling a player who is not performing."),
        ]
    else:
        response_parts.append(
            f"Let me walk you through {name} step by step, using an everyday analogy."
        )
        step_analogies = [
            ("Get oriented", "First, the system figures out what it is working with -- what tools are available, what state things are in. Like looking at your assignment before starting."),
            ("Plan the approach", "It decides the best way to accomplish the task based on the current situation. Like outlining an essay before writing it."),
            ("Execute carefully", "Each step happens in order, with checks along the way. Like showing your work on a math test."),
            ("Verify and report", "Finally, it confirms everything worked and creates a record of what happened. Like turning in your assignment and checking the grade."),
        ]

    # Build the step-by-step
    for i, (step_name, step_desc) in enumerate(step_analogies, 1):
        response_parts.append(f"\n\nStep {i} -- {step_name}: {step_desc}")

    response_parts.append(
        "\n\nThe big idea here is that AI agents, just like people, need clear processes to follow. "
        "When every step is defined and every handoff is tracked, the whole system stays safe and reliable."
    )

    return "".join(response_parts)


def generate_three_situations_response(record: dict) -> str:
    """Generate 'three situations' response."""
    name = clean_skill_name(record.get("skill_source", ""))
    content = record.get("skill_content", "") or ""
    sample = record.get("sample_packets", "") or ""
    category = record.get("category", "general")
    use_cases = extract_use_cases(content)

    response_parts = [f"Here are three real situations where you would need {name}:\n"]

    if "phone" in name.lower() or "emulator" in name.lower():
        response_parts.append(
            "1. Your virtual phone crashed and will not restart. Maybe a lock file got stuck or the emulator froze. "
            "This tool has a recovery mode that clears out the junk and gets things running again -- like force-restarting your real phone when it freezes.\n\n"
            "2. You need to test a mobile app but do not have a physical Android phone. "
            "The emulator gives you a virtual Pixel phone right on your desktop, so you can test apps, browse websites, and interact with mobile interfaces.\n\n"
            "3. You want an AI agent to use a phone interface automatically. "
            "Instead of a human tapping on a screen, the agent can navigate the emulator, open apps, and interact with mobile web pages -- all governed by safety rules."
        )
    elif "arxiv" in name.lower():
        response_parts.append(
            "1. You are writing a research paper and need to find the latest studies on a topic like 'AI safety' or 'hyperbolic geometry.' "
            "This tool searches arXiv and pulls back titles, authors, abstracts, and categories automatically.\n\n"
            "2. You found a specific paper ID (like 2301.12345) and want to extract its metadata quickly without manually browsing the site. "
            "The tool navigates directly to that paper and grabs everything you need.\n\n"
            "3. You want to build a training dataset from scientific papers. "
            "The tool can systematically search and collect paper information, saving it in structured files that can feed into AI training pipelines."
        )
    elif "cross-talk" in record.get("skill_source", "") or "communication" in name.lower() or "crosstalk" in record.get("source_type", ""):
        response_parts.append(
            "1. Two AI agents (say, Claude and Codex) are both working on the same project at the same time. "
            "They need a way to say 'I am working on file X, do not touch it' and 'I finished task Y, you can start task Z.' Without this, they would overwrite each other's work.\n\n"
            "2. An AI agent gets stuck on a task and needs to hand it off to another agent. "
            "The communication packet includes exactly what was done, what went wrong, and what the next agent should try -- like leaving detailed notes for a substitute teacher.\n\n"
            "3. You want a record of everything the AI agents did. "
            "Every message gets saved with timestamps and IDs, creating an audit trail you can review later. Think of it like a chat history for robots."
        )
    elif "governance" in name.lower() or "gate" in name.lower():
        response_parts.append(
            "1. An AI agent wants to post something to social media. Before it can, the governance gate checks whether the content is appropriate, accurate, and follows community guidelines. "
            "If anything looks wrong, it gets blocked or flagged for human review.\n\n"
            "2. A model wants to access sensitive data. The gate evaluates the request against permission rules and risk scores. "
            "Low-risk requests pass through. High-risk ones get escalated to a human decision-maker.\n\n"
            "3. You are deploying a new AI model to production. The governance gate runs a final safety check -- verifying the model meets quality standards before it goes live. "
            "Like a final exam before graduation."
        )
    elif "training" in name.lower() or "sft" in name.lower():
        response_parts.append(
            "1. You just wrote a bunch of new code and want to turn it into training examples for an AI model. "
            "The training pipeline converts your code into question-answer pairs that the model can learn from.\n\n"
            "2. You have training data scattered across multiple files and formats. "
            "This tool merges everything into one clean dataset, removes duplicates, and validates quality -- like combining study notes from different classes into one master review sheet.\n\n"
            "3. You want to push your training data to HuggingFace so other people can use it or so you can train a cloud model. "
            "The pipeline packages everything up, runs final checks, and uploads it."
        )
    elif "security" in name.lower() or "audit" in name.lower():
        response_parts.append(
            "1. You accidentally committed a file with an API key or password in it. "
            "The security audit tool scans your entire codebase for exposed secrets and alerts you before anyone else finds them.\n\n"
            "2. A dependency your project uses has a known vulnerability. "
            "The tool checks all your packages against security databases and flags anything that needs updating.\n\n"
            "3. You want to make sure your system follows security best practices before a release. "
            "The audit runs a comprehensive check -- permissions, encryption, access controls -- and gives you a pass/fail report."
        )
    elif "publish" in name.lower() or "content" in name.lower():
        response_parts.append(
            "1. You wrote a great blog post and want it on Medium, LinkedIn, Dev.to, and your own website all at once. "
            "Instead of manually formatting and posting to each platform, this tool does it for you.\n\n"
            "2. You need to schedule posts to go out at specific times across different platforms. "
            "The content publisher lets you queue things up and set release times, like scheduling tweets.\n\n"
            "3. You want to make sure everything you publish passes a governance review first. "
            "The tool checks each piece of content against your rules before it goes live, preventing accidental policy violations."
        )
    elif "youtube" in name.lower() or "video" in name.lower():
        response_parts.append(
            "1. You have 20 YouTube videos with bad descriptions and want to update them all at once. "
            "This tool lets you write a plan file, preview the changes, and push them all in one batch.\n\n"
            "2. You want to improve your video SEO (search engine optimization) by updating tags and titles. "
            "The tool lets you preview exactly what will change before committing, so you do not accidentally mess up a popular video.\n\n"
            "3. You want to track whether your metadata changes actually improved performance. "
            "After applying updates, the tool runs a review and shows you a before-and-after score."
        )
    elif "browser" in name.lower() or "web" in name.lower() or "swarm" in name.lower():
        response_parts.append(
            "1. You need to gather information from multiple websites at the same time. "
            "Instead of clicking through each one manually, the browser tool sends AI agents to visit them all in parallel.\n\n"
            "2. A website requires JavaScript to load (like a modern web app). "
            "A simple web scraper would see a blank page, but the browser agent can actually render the page and read the dynamic content.\n\n"
            "3. You want to automate a multi-step web task like filling out forms or navigating through a checkout process. "
            "The browser agent follows a script, handling clicks, typing, and navigation while safety checks watch for anything suspicious."
        )
    elif "shopify" in name.lower() or "store" in name.lower() or "revenue" in name.lower():
        response_parts.append(
            "1. You need to update prices, descriptions, or images for dozens of products in your online store. "
            "Instead of clicking through Shopify's dashboard one product at a time, this tool batch-updates everything.\n\n"
            "2. You want a daily report on revenue, downloads, and sales across all your platforms. "
            "The tool pulls data from Stripe, npm, PyPI, and Shopify and gives you one summary.\n\n"
            "3. You want to publish content and promote products at the same time. "
            "The tool coordinates posting articles, updating the store, and tracking results all in one workflow."
        )
    elif "sacred" in name.lower() or "tongue" in name.lower() or "egg" in name.lower():
        response_parts.append(
            "1. You need to encode sensitive data using the system's special language framework. "
            "The Sacred Tongues transform your data through six different encoding layers, each adding a unique mathematical weight.\n\n"
            "2. You need to create a new identity token for an AI agent or a piece of data. "
            "Sacred Eggs act like birth certificates -- they prove origin, track lineage, and carry governance stamps.\n\n"
            "3. You want to verify that data has not been tampered with. "
            "By checking the tongue encoding and egg seals, you can confirm the data is exactly as it was when it was created."
        )
    elif "deploy" in name.lower() or "fleet" in name.lower():
        response_parts.append(
            "1. You just finished training a new AI model and want to put it into production. "
            "The deployment tool runs quality checks, packages the model, and sends it to the right server.\n\n"
            "2. A deployed model is performing badly and you need to roll back to the previous version. "
            "The tool keeps version history so you can quickly swap back to what was working.\n\n"
            "3. You need the same model running on multiple cloud providers (AWS, Google Cloud, etc.) for reliability. "
            "The multi-cloud deployment tool manages the same model across different platforms."
        )
    elif "colab" in name.lower() or "compute" in name.lower():
        response_parts.append(
            "1. Your local computer is too slow to train an AI model. "
            "This tool connects to Google Colab, which gives you access to powerful GPUs for free or cheap -- like borrowing the school's gaming PC.\n\n"
            "2. You need to run a long training job that would tie up your machine for hours. "
            "By running it in the cloud, you can keep using your computer for other things.\n\n"
            "3. You want to fine-tune a language model but do not have the setup on your local machine. "
            "The tool uploads your notebook and data to Colab, runs the training, and brings back the results."
        )
    elif "session" in name.lower() or "analytics" in name.lower() or "sitrep" in name.lower():
        response_parts.append(
            "1. You want to know what happened while you were away from the computer. "
            "The status report shows what each AI agent did, what they finished, and what is still pending.\n\n"
            "2. You need to track how much money your AI sessions are costing. "
            "The analytics tool totals up token usage, model costs, and session durations across all your AI tools.\n\n"
            "3. You are starting a new work session and want a quick catch-up. "
            "Instead of reading through logs, the tool gives you a clean summary of the current state of everything."
        )
    elif "notion" in name.lower() or "obsidian" in name.lower():
        response_parts.append(
            "1. You have important design documents in Notion and need them synced with your local files. "
            "This tool fetches Notion pages and keeps your local knowledge base up to date.\n\n"
            "2. You want to query your Notion workspace to find specific information quickly. "
            "Instead of clicking through pages, you search programmatically and get structured results.\n\n"
            "3. You are building a training dataset from your notes and documentation. "
            "The tool extracts content from Notion, formats it properly, and feeds it into the training pipeline."
        )
    elif "story" in name.lower() or "lore" in name.lower() or "canon" in name.lower() or "book" in name.lower():
        response_parts.append(
            "1. You are writing a new chapter and need to make sure your characters, locations, and plot points stay consistent with everything written before. "
            "The canon writer cross-references your new content against the existing world-building.\n\n"
            "2. You want to generate an interlude or codex entry that weaves technical SCBE concepts into the story naturally. "
            "The tool knows both the tech and the lore, so it can blend them seamlessly.\n\n"
            "3. You need to produce a formatted manuscript ready for publication. "
            "The tool handles formatting for different outputs -- EPUB, DOCX, PDF -- from the same source material."
        )
    elif "git" in name.lower() or "release" in name.lower() or "dual forge" in name.lower():
        response_parts.append(
            "1. You finished a feature and want to push your code to both GitHub and GitLab at the same time. "
            "The dual push tool handles both remotes in one command, keeping them in sync.\n\n"
            "2. You need to create a new version release with a proper tag, changelog, and packaged artifacts. "
            "The release tool automates the entire process so you do not miss a step.\n\n"
            "3. Your CI pipeline failed and you need to figure out why. "
            "The tool can check build status, read error logs, and suggest fixes across both platforms."
        )
    elif "n8n" in name.lower() or "workflow" in name.lower():
        response_parts.append(
            "1. You want to automatically process new data whenever it arrives -- like triggering a training run when new records land in a folder. "
            "n8n workflows connect the trigger to the action without you writing custom code.\n\n"
            "2. You need to chain together multiple services -- Notion to processing to HuggingFace upload. "
            "The workflow tool connects these steps visually, like building a flowchart that actually runs.\n\n"
            "3. A webhook from an external service needs to trigger an internal process. "
            "n8n listens for the webhook, runs governance checks, and kicks off the right workflow automatically."
        )
    elif "disk" in name.lower() or "storage" in name.lower():
        response_parts.append(
            "1. Your computer is running out of space and you need to find what is using it all. "
            "The disk management tool scans directories and shows you the biggest space hogs.\n\n"
            "2. Cached files and temp data have piled up over weeks of development. "
            "The tool identifies safe-to-delete caches and cleans them up without touching anything important.\n\n"
            "3. You want to verify that no huge binary files accidentally ended up in your git repository. "
            "The tool scans for oversized files and warns you before they become a permanent problem."
        )
    elif "state" in name.lower() or "9d" in name.lower() or "entropy" in name.lower():
        response_parts.append(
            "1. An AI agent is behaving oddly and you need to check its current state. "
            "The state engine shows you all nine dimensions of the agent's condition -- context, time, entropy, and quantum coherence.\n\n"
            "2. You need to evolve the system's state forward in time to predict what will happen next. "
            "The dynamics engine uses mathematical equations to project how entropy and coherence will change.\n\n"
            "3. Something triggered an anomaly and you need to diagnose what dimension went wrong. "
            "The tool breaks down each dimension separately so you can pinpoint the exact source of the problem."
        )
    elif "email" in name.lower():
        response_parts.append(
            "1. You are expecting an important reply about a patent filing or business partnership. "
            "The email checker scans your inbox and highlights anything matching those keywords.\n\n"
            "2. You want a quick summary of unread messages without opening every single email. "
            "The tool checks ProtonMail and Gmail, filters out noise, and shows you just the important stuff.\n\n"
            "3. A security alert came in and you need to know about it immediately. "
            "The email tool flags high-priority security messages and surfaces them at the top of your briefing."
        )
    elif "pitch" in name.lower() or "investor" in name.lower():
        response_parts.append(
            "1. You found a potential investor and need to prepare a tailored pitch. "
            "The pipeline researches their portfolio, identifies alignment with your project, and drafts talking points.\n\n"
            "2. A grant deadline is coming up and you need to assemble your application materials. "
            "The tool organizes your existing documentation, highlights relevant achievements, and formats everything to the grant's requirements.\n\n"
            "3. You want to systematically track all your outreach -- who you contacted, when, and what happened. "
            "The pipeline logs every interaction and follow-up so nothing falls through the cracks."
        )
    elif "manifold" in name.lower() or "geometry" in name.lower() or "hyperbolic" in name.lower():
        response_parts.append(
            "1. You need to verify that a state point on the manifold is within valid bounds. "
            "The validator computes the Riemannian distance from the safe center and checks if it exceeds thresholds.\n\n"
            "2. Two AI agents report different states and you need to measure how far apart they are. "
            "The tool computes divergence between state points using toroidal geometry.\n\n"
            "3. A write operation to the manifold needs permission checking. "
            "The validator ensures the snap protocol rules are satisfied before allowing any state change."
        )
    elif "flock" in name.lower() or "swarm" in name.lower() or "fleet" in name.lower():
        response_parts.append(
            "1. You have multiple AI agents running and need to check which ones are healthy and which are stuck. "
            "The flock shepherd shows you the status of every agent, like a team roster with health stats.\n\n"
            "2. One agent is overloaded and another is idle. "
            "The shepherd can redistribute tasks so work is balanced across all agents.\n\n"
            "3. A new agent needs to join the team with a specific role. "
            "The tool spawns the agent, assigns its role (leader, validator, executor, or observer), and registers it with the governance system."
        )
    elif "ide" in name.lower() or "copilot" in name.lower():
        response_parts.append(
            "1. You are writing code and want an AI to review it for bugs and suggest improvements in real time. "
            "The copilot watches what you type and offers fixes before you even run the code.\n\n"
            "2. Your CI pipeline is failing and you need to diagnose why. "
            "The tool reads error logs, traces the issue, and suggests concrete fixes.\n\n"
            "3. You need to understand how a complex function works across multiple files. "
            "The copilot can follow function calls across the entire codebase and explain the flow."
        )
    elif "mobile" in name.lower() or "connector" in name.lower():
        response_parts.append(
            "1. You need to connect your AI system to Shopify so it can update product listings automatically. "
            "The connector tool registers the Shopify service, sets up authentication, and enables automated operations.\n\n"
            "2. A step in your workflow needs to send a Slack notification when something important happens. "
            "The connector binds your workflow goal to the Slack service and triggers messages automatically.\n\n"
            "3. You want one workflow to span multiple services -- Notion for planning, GitHub for code, Airtable for tracking. "
            "The orchestrator manages all the connectors so they work together as a single coordinated pipeline."
        )
    elif "personal" in name.lower() or "rag" in name.lower():
        response_parts.append(
            "1. You need to quickly remember where a specific file lives in the 500+ file codebase. "
            "Instead of searching through folders, you ask the RAG and it tells you the exact path.\n\n"
            "2. Someone asks about a formula or concept from the SCBE architecture. "
            "The knowledge base has the answer cached and returns it instantly, no file searching needed.\n\n"
            "3. You are not sure if a feature already exists before building it. "
            "The RAG checks the existing codebase knowledge and tells you if something similar is already there and where to find it."
        )
    elif "longform" in name.lower():
        response_parts.append(
            "1. A task requires dozens of steps spanning multiple coding sessions. "
            "The longform tool creates checkpoints so you can stop, pick up later, and not lose your place.\n\n"
            "2. Multiple AI agents need to continue each other's work on the same task. "
            "The checkpoint files contain everything the next agent needs to resume without starting over.\n\n"
            "3. A complex implementation keeps failing midway and you need to debug where it goes wrong. "
            "The checkpoints show exactly which step succeeded and which failed, making diagnosis much easier."
        )
    elif "transcri" in name.lower() or "audio" in name.lower():
        response_parts.append(
            "1. You recorded a meeting or brainstorming session and need a text version. "
            "The transcription tool converts speech to text so you can search and reference what was said.\n\n"
            "2. You want to add subtitles to a video for accessibility. "
            "The tool generates timestamped text that can be used as captions.\n\n"
            "3. You have audio training data that needs to be converted to text for an AI model. "
            "The transcription pipeline processes audio files in bulk and outputs structured text data."
        )
    elif "art" in name.lower() or "image" in name.lower() or "visual" in name.lower():
        response_parts.append(
            "1. You need a character portrait for a story chapter or game asset. "
            "The art generator creates illustrations from text descriptions using AI image models.\n\n"
            "2. You want a hero image for a website or social media post. "
            "The tool generates eye-catching visuals that match your project's style.\n\n"
            "3. You need a technical diagram or architecture visualization. "
            "Instead of drawing it by hand, you describe what you want and the generator creates it."
        )
    elif "research" in name.lower():
        response_parts.append(
            "1. Someone makes a claim about AI safety and you want to verify it with real sources. "
            "The research tool checks multiple outlets, finds primary sources, and returns dated evidence with confidence scores.\n\n"
            "2. You need current market data or recent news for a business decision. "
            "The tool searches mainstream and niche sources, not just the first Google result, and flags how reliable each source is.\n\n"
            "3. You are building a literature review and need to systematically collect information on a topic. "
            "The pipeline structures the research into categories, tracks what has been covered, and identifies gaps."
        )
    elif "context" in name.lower() and "catalog" in name.lower():
        response_parts.append(
            "1. A new type of task comes in and the system needs to figure out which tools and resources to use. "
            "The catalog maps the task type to the right archetype, telling the system exactly what is needed.\n\n"
            "2. You want to understand how much a particular operation should cost in terms of computing credits. "
            "Each archetype in the catalog has credit values assigned, so you can predict costs upfront.\n\n"
            "3. You are extending the system with new capabilities and need to register them properly. "
            "The catalog provides a template for adding new task types with all the right connections to credit categories and Sacred Tongue denominations."
        )
    elif "credit" in name.lower() or "ledger" in name.lower():
        response_parts.append(
            "1. An AI agent just did expensive work and needs to log the cost. "
            "The credit ledger records the transaction with a blockchain-style hash, making it tamper-proof.\n\n"
            "2. You want to check how many computing credits are left in your budget. "
            "The ledger tracks balances across all AI agents and flags when you are running low.\n\n"
            "3. Two AI systems need to exchange computing resources fairly. "
            "The credit system acts as a neutral bank, ensuring neither side overspends or underpays."
        )
    elif "webtoon" in name.lower() or "manhwa" in name.lower() or "comic" in name.lower() or "storyboard" in name.lower():
        response_parts.append(
            "1. You wrote a novel chapter and want to turn key scenes into comic panels. "
            "The storyboard tool breaks the text into visual beats and generates panel scripts.\n\n"
            "2. You need consistent character designs across dozens of panels. "
            "The tool maintains reference sheets so characters look the same from panel to panel.\n\n"
            "3. You want vertical-scroll webtoon formatting instead of traditional comic page layouts. "
            "The tool arranges panels for the vertical scroll reading experience popular on platforms like Webtoon and Tapas."
        )
    elif "tuxemon" in name.lower() or "game" in name.lower():
        response_parts.append(
            "1. You want to add a new creature to the Tuxemon game with custom stats and abilities. "
            "The creator tool generates the database entry, sprite references, and encounter configuration.\n\n"
            "2. A map is not rendering correctly -- tiles are missing or showing black gaps. "
            "The debug tool checks tileset references, camera settings, and rendering pipeline for issues.\n\n"
            "3. You want to create a new game area with events, NPCs, and wild encounters. "
            "The map editor builds the TMX tile map, places event triggers, and configures transitions to other areas."
        )
    elif "skill" in name.lower() and "creat" in name.lower():
        response_parts.append(
            "1. You identified a repetitive task that the AI does often and want to turn it into a reusable skill. "
            "The creator scaffolds the SKILL.md file with proper frontmatter, workflow steps, and guardrails.\n\n"
            "2. An existing skill needs updating with new capabilities or better instructions. "
            "The tool edits the skill definition while maintaining the correct format.\n\n"
            "3. You want to verify that a skill you wrote actually works before deploying it. "
            "The creator includes validation steps that check the skill follows the SCBE format and has all required sections."
        )
    elif "patch" in name.lower() or "diff" in name.lower():
        response_parts.append(
            "1. You made changes to multiple files and want to review exactly what changed before committing. "
            "The diff viewer creates a visual side-by-side comparison that is easy to read.\n\n"
            "2. You need to share your changes with a teammate who does not have access to the code editor. "
            "The tool renders the diff as an HTML page or image that anyone can view.\n\n"
            "3. You want to compare two different versions of a file to understand when a bug was introduced. "
            "The viewer highlights exactly which lines changed between versions."
        )
    elif "pdf" in name.lower():
        response_parts.append(
            "1. You need to combine several report files into one PDF for distribution. "
            "The tool merges multiple documents in the order you specify.\n\n"
            "2. A large PDF needs to be split into individual chapters or sections. "
            "The tool extracts specific page ranges into separate files.\n\n"
            "3. You want to generate a formatted report from data with proper headers, tables, and page numbers. "
            "The PDF tool creates professional documents from structured content."
        )
    else:
        if use_cases:
            for i, uc in enumerate(use_cases[:3], 1):
                response_parts.append(f"{i}. {uc}\n\n")
        else:
            response_parts.append(
                f"1. When you need to set up or configure the {name} component for the first time. "
                "Like getting a new app installed and configured on your phone.\n\n"
                f"2. When something in the {name} system breaks or stops working correctly. "
                "Like troubleshooting when your Wi-Fi drops -- you check the obvious things first, then dig deeper.\n\n"
                f"3. When you want to extend {name} with new capabilities. "
                "Like adding a new feature to a project you have been building all semester."
            )

    return "".join(response_parts)


def generate_intent_response(record: dict) -> str:
    """Generate response explaining intent types from cross-talk packets."""
    instruction = record.get("instruction", "")
    sample = record.get("sample_packets", "") or ""

    # Extract intent names from instruction
    intent_match = re.findall(r"(\w+(?:[-_]\w+)*)", instruction)
    intents = [i for i in intent_match if "_" in i or any(kw in i.lower() for kw in ["ready", "update", "claim", "evidence", "unknown", "handoff", "status", "critical", "lease", "done", "blocked"])]

    # If we found specific intents in the instruction, explain those
    if not intents:
        # Try to extract from sample packets
        if sample:
            for m in re.finditer(r'"intent":\s*"([^"]+)"', sample):
                intents.append(m.group(1))

    response_parts = [
        "In the SCBE system, AI agents communicate by sending message packets with an 'intent' field that says exactly what the message is about. "
        "Think of intents like the subject line of an email -- they tell the reader what to expect before they even open it.\n\n"
        "Here is what each intent means:\n\n"
    ]

    intent_explanations = {
        "claim_colab_worker": "claim_colab_worker -- This is like raising your hand and saying 'I am taking this computer.' The agent is reserving a cloud computing session so no other agent tries to use the same one at the same time.",
        "colab_worker_ready": "colab_worker_ready -- The cloud computing session is set up and waiting. Like saying 'The computer is on, logged in, and ready to go.' Other agents know they can now send work to it.",
        "colab_worker_evidence": "colab_worker_evidence -- The agent is sharing proof of what it did during the computing session. Screenshots, output logs, saved files -- like turning in your homework with your work shown.",
        "critical-update": "critical-update -- Something important happened that other agents need to know about RIGHT NOW. Like a fire alarm -- drop what you are doing and pay attention. This might be a security issue, a major failure, or an urgent change.",
        "unknown": "unknown -- The system received a message it does not recognize. Like getting a note in class written in a language you do not speak. The system logs it and flags it for review rather than ignoring it.",
        "handoff": "handoff -- One agent is passing its work to another. Like a relay race baton pass -- the first runner hands off to the second with clear instructions about the race state.",
        "status": "status -- A simple progress update. Like texting your group chat 'halfway done with my part.' No action needed, just keeping everyone informed.",
        "blocked": "blocked -- The agent is stuck and cannot continue. Like telling your teacher 'I cannot do problem 5 because I do not understand problem 4.' It needs help or a different approach.",
        "done": "done -- The task is complete. Like turning in a finished assignment. Other agents waiting on this work can now proceed.",
        "lease_claimed": "lease_claimed -- A resource (like a computing session) has been officially reserved. Like signing out a library book -- it is yours for the duration of the lease.",
    }

    explained = set()
    for intent in intents:
        key = intent.lower().replace("-", "_").replace(" ", "_")
        if key in intent_explanations and key not in explained:
            response_parts.append(f"- {intent_explanations[key]}\n\n")
            explained.add(key)

    # If we did not find specific matches, give general explanations
    if not explained:
        for key in ["claim_colab_worker", "colab_worker_ready", "critical-update", "unknown", "colab_worker_evidence"]:
            response_parts.append(f"- {intent_explanations.get(key.replace('-','_'), '')}\n\n")

    response_parts.append(
        "The key idea is that every message between AI agents has a clear label. "
        "No guessing, no ambiguity. This makes the whole system predictable and auditable -- "
        "you can always look at the intent to understand what an agent was trying to do."
    )

    return "".join(response_parts)


def generate_status_field_response(record: dict) -> str:
    """Generate response explaining status fields from cross-talk packets."""
    response = (
        "In the SCBE system, every message between AI agents carries a 'status' field that tells everyone "
        "where things stand. Think of it like the status updates on a food delivery app -- you can always see "
        "whether your order is being prepared, on its way, or delivered.\n\n"
        "Here are the main status values:\n\n"
        "- in_progress -- The agent is actively working on the task. Like seeing 'Your order is being prepared' "
        "on the delivery app. Other agents know not to duplicate this work.\n\n"
        "- blocked -- The agent hit a wall and cannot continue without help. Like a delivery driver finding the "
        "road closed. The message includes what the blocker is and what is needed to unblock it.\n\n"
        "- done -- The task is finished. Like 'Delivered!' Everything the agent produced is attached or linked "
        "in the message so the next agent can pick it up.\n\n"
        "- failed -- Something went wrong and the task could not be completed. Like 'Delivery failed -- address "
        "not found.' The error details are included so someone can diagnose what happened.\n\n"
        "Why does this matter? Because when you have multiple AI agents working at the same time, they need a "
        "simple, reliable way to coordinate. The status field is that coordination mechanism. Without it, agents "
        "might duplicate work, wait forever for something that already failed, or miss that a critical task is blocked."
    )
    return response


def generate_packet_structure_response(record: dict) -> str:
    """Generate response explaining cross-talk packet structure."""
    response = (
        "A cross-talk packet is basically a structured note that AI agents pass to each other. "
        "Think of it like a standardized form you fill out for a group project update.\n\n"
        "Here are the key parts of a packet:\n\n"
        "- packet_id: A unique name for this specific message. Like a tracking number on a package -- "
        "no two packets have the same ID, so you can always find a specific one.\n\n"
        "- sender and recipient: Who wrote it and who should read it. Like the 'From' and 'To' on an envelope.\n\n"
        "- intent: What the message is about (handoff, status update, critical alert, etc.). "
        "Like the subject line of an email.\n\n"
        "- status: Where the task stands (in_progress, blocked, done). Like a progress bar.\n\n"
        "- summary: A short human-readable description. Like a tweet-length version of the full message.\n\n"
        "- proof: Evidence of what was done -- file paths, command outputs, screenshots. "
        "Like attaching your homework to an email instead of just saying 'I did it.'\n\n"
        "- next_action: What should happen next. Like writing 'Your turn to do the conclusion' "
        "at the bottom of your group project note.\n\n"
        "- risk: How risky the current situation is (low, medium, high). Like a weather warning level.\n\n"
        "The entire packet gets saved with timestamps so there is a permanent record of every handoff. "
        "This is what makes the multi-agent system trustworthy -- everything is documented, "
        "everything is traceable, and nothing happens in secret."
    )
    return response


def generate_layer14_response(record: dict) -> str:
    """Generate response explaining Layer 14 telemetry."""
    response = (
        "Layer 14 is the telemetry and monitoring layer of the SCBE system's 14-layer security pipeline. "
        "Think of it like the dashboard on a car -- it shows you speed, fuel level, engine temperature, "
        "and warning lights all in one place.\n\n"
        "Here is what the Layer 14 fields mean:\n\n"
        "- energy: How much processing power or effort went into this action. Like checking how hard "
        "your car engine is working.\n\n"
        "- stability: How reliable and consistent the system is right now. A score of 1.0 means everything "
        "is perfectly stable. Like checking that all four tires have the right pressure.\n\n"
        "- verification_score: How confident the system is that the action was correct. Like a spellchecker's "
        "confidence that a word is spelled right.\n\n"
        "- anomaly_ratio: How unusual or unexpected the current behavior is. Zero means everything is normal. "
        "Higher numbers mean something weird is happening. Like a smoke detector -- zero smoke is normal.\n\n"
        "- signal_class: A label describing what type of event this is. Like categorizing an email as "
        "'newsletter,' 'personal,' or 'urgent.'\n\n"
        "Why does this matter for AI safety? Because you cannot fix what you cannot see. Layer 14 makes "
        "the invisible visible -- it turns abstract AI behavior into concrete numbers that humans and "
        "other AI agents can monitor, compare, and act on. If anything drifts out of normal range, "
        "the system catches it immediately."
    )
    return response


def classify_instruction(instruction: str, source_type: str = "") -> str:
    """Classify instruction into response type."""
    inst_lower = instruction.lower()
    if "what is" in inst_lower and "explain" in inst_lower:
        return "what_is"
    if "walk me through" in inst_lower or "step by step" in inst_lower:
        return "step_by_step"
    if "three situations" in inst_lower or "three real" in inst_lower:
        return "three_situations"
    if "intent" in inst_lower and ("mean" in inst_lower or "plain english" in inst_lower):
        return "intent_explain"
    if "status" in inst_lower and ("field" in inst_lower or "mean" in inst_lower or "values" in inst_lower):
        return "status_explain"
    if "packet" in inst_lower and ("structure" in inst_lower or "field" in inst_lower or "part" in inst_lower or "look like" in inst_lower):
        return "packet_structure"
    if "layer" in inst_lower and "14" in inst_lower:
        return "layer14"
    if "cross-talk" in inst_lower or "crosstalk" in inst_lower:
        if "what is" in inst_lower:
            return "what_is"
        return "packet_structure"
    if "risk" in inst_lower and ("level" in inst_lower or "field" in inst_lower or "assess" in inst_lower):
        return "risk_explain"
    if "governance" in inst_lower and ("stamp" in inst_lower or "gate" in inst_lower):
        return "governance_explain"
    if "rail" in inst_lower or "P+" in instruction or "D-" in instruction:
        return "rails_explain"
    if "ledger" in inst_lower and ("deliver" in inst_lower or "route" in inst_lower or "lane" in inst_lower):
        return "ledger_explain"
    if "lease" in inst_lower:
        return "lease_explain"
    # Default based on source type
    if source_type == "crosstalk_tutorial":
        return "packet_structure"
    return "what_is"


def generate_risk_response(record: dict) -> str:
    """Explain risk levels."""
    return (
        "In the SCBE system, every action gets a risk rating -- low, medium, or high. "
        "Think of it like a weather forecast: sunny (low risk), cloudy with a chance of rain (medium risk), "
        "or severe storm warning (high risk).\n\n"
        "Low risk means the action is routine and safe. Like walking to class on a normal day. "
        "The system processes it quickly without extra checks.\n\n"
        "Medium risk means something about the situation is unusual and deserves a closer look. "
        "Like walking to class when there is a wet floor sign -- you proceed, but carefully. "
        "The system might add extra logging or require a second agent to verify.\n\n"
        "High risk means the action could cause real problems if it goes wrong. "
        "Like a tornado warning -- you do not just keep walking. "
        "High-risk actions get escalated to governance gates, where they face stricter checks "
        "and may require human approval before proceeding.\n\n"
        "The risk field is attached to every cross-talk packet between AI agents. "
        "This means every handoff includes a clear signal about how carefully the next agent should proceed. "
        "It is one of the simplest but most important parts of the AI safety system -- "
        "because knowing how dangerous something is should come BEFORE you do it, not after."
    )


def generate_governance_explain_response(record: dict) -> str:
    """Explain governance stamps."""
    return (
        "Governance stamps are like the stamps a teacher puts on your paper to show it was reviewed and approved. "
        "In the SCBE system, every important action gets stamped with a governance record that says: "
        "who did it, when they did it, what rules were checked, and whether it passed.\n\n"
        "Think of it like airport security. Your bag goes through the X-ray machine (the governance check), "
        "and if everything is fine, it gets a green light (ALLOW stamp). If something looks suspicious, "
        "it gets pulled aside for manual inspection (QUARANTINE stamp). If it is clearly dangerous, "
        "it gets stopped completely (DENY stamp). And if it needs a supervisor's opinion, "
        "it gets sent up the chain (ESCALATE stamp).\n\n"
        "These four outcomes -- ALLOW, QUARANTINE, ESCALATE, DENY -- are the core decisions "
        "in the SCBE governance system. Every action, every data transfer, every publication "
        "passes through at least one governance gate.\n\n"
        "The stamp includes a timestamp, the agent ID, the risk level, and the specific checks that were run. "
        "This creates a complete audit trail -- if anything goes wrong later, you can trace back exactly "
        "who approved what and why. It is like having a security camera for AI decisions."
    )


def generate_rails_response(record: dict) -> str:
    """Explain P+/P-/D+/D- rails."""
    return (
        "Rails in the SCBE system are like the guardrails on a bowling lane -- they keep the action "
        "going in the right direction. There are four types, and they use plus and minus signs "
        "to show whether something is being added or prevented.\n\n"
        "P+ (Positive Permission): Things the agent IS allowed to do. Like a hall pass that says "
        "'You may go to the library.' These are explicit permissions.\n\n"
        "P- (Negative Permission): Things the agent is NOT allowed to do. Like a rule that says "
        "'No phones in class.' These are explicit restrictions.\n\n"
        "D+ (Positive Duty): Things the agent MUST do. Like homework that is required -- "
        "you cannot skip it. These are mandatory actions or checks.\n\n"
        "D- (Negative Duty): Things the agent must NOT do under any circumstances. Like a zero-tolerance rule. "
        "These are hard limits that cannot be overridden.\n\n"
        "Every cross-talk packet between agents includes a rails section. When Agent A hands work to Agent B, "
        "the rails tell Agent B exactly what it can do, cannot do, must do, and must never do.\n\n"
        "Why is this important for AI safety? Because AI agents should not just be told WHAT to do -- "
        "they should also be told what NOT to do. Rails make the boundaries explicit, "
        "so there is no ambiguity about acceptable behavior. It is one of the key differences "
        "between an AI that just follows instructions and an AI that follows instructions safely."
    )


def generate_ledger_response(record: dict) -> str:
    """Explain ledger delivery lanes."""
    return (
        "The ledger in SCBE cross-talk packets works like a mail carrier's delivery route. "
        "It says where the message should go and how it should get there.\n\n"
        "There are three main delivery lanes:\n\n"
        "- dated_json: The packet gets saved as a JSON file in a dated folder. "
        "Like putting a letter in a filing cabinet organized by date. Good for finding messages later.\n\n"
        "- jsonl_bus: The packet gets appended to a running log file. "
        "Like a chat history that keeps growing. Good for seeing the full timeline of what happened.\n\n"
        "- obsidian: The packet gets mirrored into Obsidian notes. "
        "Like pinning an important message to a bulletin board. Good for human-readable overviews.\n\n"
        "The delivery_mode field says whether the packet goes to all lanes or just specific ones. "
        "'all_lanes' is the default -- like sending a group text instead of individual messages.\n\n"
        "Why three lanes instead of one? Redundancy and different use cases. "
        "The JSON files are great for machines to process. The JSONL bus is great for streaming analysis. "
        "The Obsidian notes are great for humans to read. By delivering to all three, "
        "the system ensures nothing is lost and everyone -- human or AI -- can access the information "
        "in the format that works best for them."
    )


def generate_lease_response(record: dict) -> str:
    """Explain lease system."""
    return (
        "A lease in the SCBE system is like checking out a book from the library. "
        "You get exclusive access to a resource for a set amount of time, "
        "and when your time is up, it becomes available for someone else.\n\n"
        "Here is how it works in the AI world:\n\n"
        "When an AI agent needs to use a shared resource -- like a cloud computing session on Google Colab -- "
        "it 'claims a lease.' This is like signing the checkout card. The lease includes:\n\n"
        "- lease_id: A unique tracking number.\n"
        "- owner: Which agent claimed it.\n"
        "- provider: Where the resource lives (Colab, AWS, etc.).\n"
        "- lease_seconds: How long the agent gets to use it (usually 3600 seconds, which is one hour).\n"
        "- claimed_at: When the clock started.\n"
        "- expires_at: When the agent must give it back.\n\n"
        "Why do AI agents need leases? The same reason you need a reservation at a busy restaurant. "
        "Without leases, two agents might try to use the same computing session at the same time, "
        "causing conflicts and wasted resources. The lease system prevents this by making resource "
        "access organized and predictable.\n\n"
        "When the lease expires, the agent must release the resource. If it does not, "
        "the system can forcibly reclaim it -- like the library sending you a late notice. "
        "This keeps shared resources flowing smoothly across the whole agent team."
    )


def generate_generic_crosstalk_response(record: dict) -> str:
    """Fallback for unclassified crosstalk tutorial questions."""
    instruction = record.get("instruction", "")
    return (
        f"Great question! Let me break this down in simple terms.\n\n"
        "In the SCBE system, AI agents work together like a team of students on a group project. "
        "They need to communicate clearly, share their work, and coordinate so nobody steps on "
        "anyone else's toes.\n\n"
        "The cross-talk system is how they do this. Every message between agents follows a standard "
        "format -- like filling out a form instead of writing random notes. This means:\n\n"
        "- Every message has a unique ID (so you can track it)\n"
        "- Every message says who sent it and who should read it\n"
        "- Every message includes what was done and what should happen next\n"
        "- Every message carries a risk level so the receiver knows how careful to be\n\n"
        "The messages get saved in multiple places -- machine-readable files for AI agents, "
        "human-readable notes for people, and running logs for analysis. This triple backup "
        "means nothing gets lost.\n\n"
        "The bigger picture: when AI agents can communicate clearly and predictably, "
        "the whole system becomes safer and more reliable. No miscommunication, no lost context, "
        "no agents going rogue. Everything is documented and auditable."
    )


def flesh_out(response: str, record: dict, target_min: int = 150) -> str:
    """Expand a response to meet the target word count by adding context-appropriate detail."""
    words = len(response.split())
    if words >= target_min:
        return response

    name = clean_skill_name(record.get("skill_source", ""))
    category = record.get("category", "general")
    desc = record.get("skill_description", "")
    content = record.get("skill_content", "") or ""
    concepts = extract_key_concepts(content)

    extras = []

    # Add detail about what it specifically handles from skill_content
    if concepts and words < target_min:
        concept_strs = [c.lower() for c in concepts[:4] if len(c) > 5 and not c.startswith("`")]
        if concept_strs:
            extras.append(
                f"\n\nLooking more closely at what {name} covers, some of its core areas include: "
                + ", ".join(concept_strs) + ". "
                "Each of these areas represents a different piece of the puzzle. "
                "When they all work together, you get a system that is more than the sum of its parts -- "
                "like how a basketball team is better than five people playing alone."
            )

    # Add AI safety connection
    if words + len(" ".join(extras).split()) < target_min:
        safety_hooks = {
            "infrastructure": (
                "In the bigger picture of AI safety, infrastructure tools like this make sure the "
                "foundation is solid. If the base layer has problems -- crashed emulators, stale connections, "
                "broken services -- then everything built on top of it becomes unreliable. "
                "It is like making sure the school building itself is safe before worrying about lesson plans."
            ),
            "browser": (
                "When it comes to AI safety, browser tools carry extra responsibility. "
                "The internet is full of misleading information, malicious content, and privacy risks. "
                "A governed browser tool does not just fetch web pages -- it verifies sources, "
                "checks for prompt injection attacks, and makes sure the AI is not being tricked. "
                "Think of it as browsing the internet with a built-in fact-checker and bodyguard."
            ),
            "ai_coordination": (
                "For AI safety, coordination between agents is absolutely critical. "
                "Imagine two self-driving cars approaching the same intersection at the same time. "
                "Without clear communication protocols, they could crash into each other. "
                "The same applies to AI agents -- without standardized messages and clear handoffs, "
                "agents could conflict with each other, duplicate work, or make contradictory decisions. "
                "That is why every message follows a strict format with sender, recipient, intent, and status."
            ),
            "security": (
                "Security in AI is not just about stopping hackers -- it is about building a system "
                "that is trustworthy by design. Every audit, every scan, every permission check "
                "adds another layer of protection. Think of it like the layers of security at an airport: "
                "ticket check, ID verification, bag scan, metal detector. Each layer catches "
                "something the others might miss. The SCBE system works the same way with its "
                "14-layer security pipeline."
            ),
            "training": (
                "Training is where AI models learn to be good at their jobs. But training also carries risks -- "
                "bad data can teach bad habits, biased examples can create biased models, "
                "and poisoned training sets can embed hidden vulnerabilities. "
                "That is why SCBE governance checks every piece of training data before it enters the pipeline. "
                "Quality in, quality out -- like how eating junk food versus real food affects your performance."
            ),
            "publishing": (
                "Publishing content from AI systems is a real responsibility. "
                "Once something is posted online, it is hard to take back. "
                "That is why the governance layer reviews everything before it goes live -- "
                "checking for accuracy, appropriateness, and alignment with the project's values. "
                "It is like having an editor who reads every article before the newspaper prints it."
            ),
            "governance": (
                "Governance is the heart of the whole SCBE system. "
                "Without governance, AI agents would be like students in a school with no rules -- "
                "some would be fine, but others might cause chaos. "
                "The governance layer ensures that every action, every decision, and every output "
                "meets a minimum standard of safety and quality. "
                "It is what makes the difference between AI that is merely powerful and AI that is trustworthy."
            ),
            "general": (
                "Every tool in the SCBE system connects to the bigger mission of making AI safe and useful. "
                "No single tool does everything -- they work together like instruments in an orchestra. "
                "The key insight is that safety is not a feature you bolt on at the end. "
                "It is baked into every layer, every tool, and every interaction from the start. "
                "That is what makes this approach different from systems that treat safety as an afterthought."
            ),
            "data": (
                "Data management might sound boring, but it is one of the most important pieces of AI safety. "
                "If your data is messy, your AI will be messy. If your data is organized and verified, "
                "your AI has a much better foundation. Think of it like cooking -- "
                "the best chefs start with quality ingredients, properly prepared. "
                "This tool makes sure the data 'ingredients' are clean, organized, and ready to use."
            ),
            "game": (
                "Even game-related tools connect to the broader AI safety picture. "
                "Games are great testing grounds for AI behavior -- you can observe how agents make decisions, "
                "handle surprises, and interact with each other in a controlled environment. "
                "What you learn from game AI directly applies to real-world AI safety, "
                "because the underlying patterns of decision-making and coordination are the same."
            ),
            "creative": (
                "Creative tools in the AI safety ecosystem might seem like an odd fit, "
                "but they serve an important purpose. When AI generates creative content -- stories, art, code -- "
                "it needs to follow the same governance rules as everything else. "
                "The creative output should be original, appropriate, and consistent with the project's values. "
                "These tools ensure that AI creativity stays within safe bounds without stifling imagination."
            ),
        }
        hook = safety_hooks.get(category, safety_hooks["general"])
        extras.append(f"\n\n{hook}")

    # Add practical connection
    if words + len(" ".join(extras).split()) < target_min:
        extras.append(
            f"\n\nIf you are curious about trying this yourself, {name} is part of the SCBE-AETHERMOORE project, "
            "which you can find on GitHub. The whole system is built with the idea that AI should be "
            "powerful AND safe -- not one or the other. Every tool, including this one, "
            "is designed to make AI agents more capable while keeping them accountable for their actions."
        )

    return response + "".join(extras)


def generate_response(record: dict) -> str:
    """Main dispatcher: generate appropriate response based on instruction type."""
    instruction = record.get("instruction", "")
    source_type = record.get("source_type", "")

    rtype = classify_instruction(instruction, source_type)

    if rtype == "what_is":
        raw = generate_what_is_response(record)
    elif rtype == "step_by_step":
        raw = generate_step_by_step_response(record)
    elif rtype == "three_situations":
        raw = generate_three_situations_response(record)
    elif rtype == "intent_explain":
        raw = generate_intent_response(record)
    elif rtype == "status_explain":
        raw = generate_status_field_response(record)
    elif rtype == "packet_structure":
        raw = generate_packet_structure_response(record)
    elif rtype == "layer14":
        raw = generate_layer14_response(record)
    elif rtype == "risk_explain":
        raw = generate_risk_response(record)
    elif rtype == "governance_explain":
        raw = generate_governance_explain_response(record)
    elif rtype == "rails_explain":
        raw = generate_rails_response(record)
    elif rtype == "ledger_explain":
        raw = generate_ledger_response(record)
    elif rtype == "lease_explain":
        raw = generate_lease_response(record)
    else:
        if source_type == "crosstalk_tutorial":
            raw = generate_generic_crosstalk_response(record)
        else:
            raw = generate_what_is_response(record)

    return flesh_out(raw, record, target_min=170)


def main():
    records = []
    with open(INPUT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} stub records")

    output_records = []
    for i, record in enumerate(records):
        # Generate response
        response = generate_response(record)

        # Build output record, stripping skill_content and sample_packets
        out = {}
        for key, value in record.items():
            if key in ("skill_content", "sample_packets"):
                continue
            if key == "response":
                out[key] = response
            else:
                out[key] = value

        output_records.append(out)

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(records)}")

    # Write output
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for rec in output_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(output_records)} records to {OUTPUT}")

    # Quick stats
    word_counts = []
    for rec in output_records:
        words = len(rec["response"].split())
        word_counts.append(words)

    avg_words = sum(word_counts) / len(word_counts)
    min_words = min(word_counts)
    max_words = max(word_counts)
    print(f"Response word counts: min={min_words}, avg={avg_words:.0f}, max={max_words}")

    # Check for empty responses
    empty = sum(1 for rec in output_records if not rec["response"].strip())
    print(f"Empty responses: {empty}")


if __name__ == "__main__":
    main()
