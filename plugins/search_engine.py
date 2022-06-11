from typing import TypeVar, Callable, List

T = TypeVar("T")


class KMP:

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self.pi = self.computeLPSArray()

    def computeLPSArray(self):
        length = 0  # length of the previous longest prefix suffix
        M = len(self.pattern)
        lps = [0] * M
        i = 1

        # the loop calculates lps[i] for i = 1 to M-1 
        while i < M:
            if self.pattern[i] == self.pattern[length]:
                length += 1
                lps[i] = length
                i += 1
            else:
                # This is tricky. Consider the example. 
                # AAACAAAA and i = 7. The idea is similar
                # to search step. 

                if length != 0:
                    length = lps[length - 1]
                    # Also, note that we do not increment i here 
                else:
                    lps[i] = 0
                    i += 1

        return lps

    # Python program for KMP Algorithm 

    def KMPSearch(self, txt):
        pat = self.pattern
        M = len(pat)
        N = len(txt)

        lps = self.pi

        i = 0  # index for txt[]
        j = 0  # index for pat[]

        while i < N:

            if pat[j] == txt[i]:
                i += 1
                j += 1

            if j == M:
                return True

            # mismatch after j matches 
            elif i < N and pat[j] != txt[i]:
                # Do not match lps[0..lps[j-1]] characters, 
                # they will match anyway 
                if j != 0:
                    j = lps[j - 1]
                else:
                    i += 1
        return False


def search(query: str, documents: List[T], get_title: Callable[[T], str], get_text: Callable[[T], str]):
    query = query.lower()
    qwords = query.split()
    qkmp = [KMP(word) for word in qwords]
    ranking = []
    for doc in documents:
        score = 0
        title = get_title(doc).lower()
        text = get_text(doc).lower()
        for kmp in qkmp:
            if kmp.KMPSearch(text):
                score += 1
            if kmp.KMPSearch(title):
                score += 5
            if title == query:
                score += 1000
        if score > 0:
            ranking.append((score, len(ranking), doc))
    ranking.sort()
    ranking.reverse()
    return [doc for (_, _, doc) in ranking]
