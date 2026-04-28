class Node:
    def __init__(self, max_retries: int = 0, wait: int = 0):
        self._next = None
        self.max_retries = max_retries
        self.wait = wait
        self.cur_retry = 0

    def __rshift__(self, other):
        self._next = other
        return other

    # lifecycle hooks expected by referenced nodes
    def prep(self, shared):
        return None

    def exec(self, prep_res):
        return None

    def post(self, shared, prep_res, exec_res):
        return None


class BatchNode(Node):
    def prep(self, shared):
        return []

    # exec will be called for each item by Flow
    def exec(self, item):
        return item

    def post(self, shared, prep_res, exec_res_list):
        return None


class Flow:
    def __init__(self, start: Node):
        self.start = start

    def run(self, shared: dict):
        """Run a simple linear flow following `>>` links between nodes.

        Each node runs: prep(shared) -> exec(prep_res) -> post(shared, prep_res, exec_res).
        If a node is a BatchNode, its exec is invoked for each item in the iterable returned by prep.
        """
        node = self.start
        while node is not None:
            # call prep
            prep_res = node.prep(shared)

            # call exec
            if isinstance(node, BatchNode):
                # prep_res is expected to be iterable
                results = []
                for item in prep_res:
                    res = node.exec(item)
                    results.append(res)
                exec_res = results
            else:
                exec_res = node.exec(prep_res)

            # call post
            node.post(shared, prep_res, exec_res)

            # advance to next node linked via __rshift__ operator
            node = getattr(node, "_next", None)
