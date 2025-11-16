class VRPModel:
    def __init__(self):
        self.nodes = []

    def from_solomon_dict(self, data):
        # data is expected to be the dict returned by solomon_loader.load_instance
        self.nodes = data.get('lines', [])
        return self

    def summary(self):
        return {'n_nodes': len(self.nodes)}
