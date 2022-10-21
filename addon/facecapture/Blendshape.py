import numpy as np

class BlendshapeMesh:
    def __init__(self, data):
        self.basis = data[0]
        self.dif = data[1:] - self.basis
        nb, nv, _ = self.dif.shape
        self.weights = np.zeros(nb)

    def vertices(self, weights):
        return self.basis + np.tensordot(weights, self.dif, axes=((0, 0)))

    def get_weights(self, landmarks):
        nb, nv, nd = self.dif.shape

        if nb == 0:
            error = self.__costFunction(self.basis, landmarks)
            return self.weights, error

        A = self.dif.transpose(1, 2, 0).reshape(-1,nb)
        B = (landmarks-self.basis).reshape(-1,1)

        # Calculate minimization of ||Ax-b||^2
        x, residuals, rank, s = np.linalg.lstsq(A, B, rcond = None)

        return x, residuals

    def __costFunction(self, obj1, obj2) :
        D = obj1 - obj2
        return np.tensordot(D, D)


if __name__ == '__main__':
    data = np.array([
        [(1, 2, 3), (4, 5, 6)], # Basis
        [(2, 3, 4), (3, 4, 5)], # Key 0
        [(1, 2, 3), (3, 4, 6)], # Key 1
        [(3, 1, 4), (5, 4, 7)], # Key 2
        [(4, 3, 1), (4, 4, 1)], # Key 3
    ])
    mesh = BlendshapeMesh(data)

    weights = np.array([0.9, 0.1, 0.6, 0.5])
    landmarks = mesh.vertices(weights)
    print('landmarks\n', landmarks)

    weights, error = mesh.get_weights(landmarks)
    print(weights)
    print('error = ', error)
    verts = mesh.vertices( weights )
    print('verts\n', verts)
