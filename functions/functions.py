import string, random


def zufallswort(length):
    zeichen = string.ascii_lowercase
    return ''.join(random.choice(zeichen) for i in range(length))


    # smog = textstat.smog_index(post.content)
    # fkg = textstat.flesch_kincaid_grade(post.content)
    # ari= textstat.automated_readability_index(post.content)
    # dcrs= textstat.dale_chall_readability_score(post.content)
    # dw= textstat.difficult_words(post.content)
    # gf= textstat.gunning_fog(post.content)



