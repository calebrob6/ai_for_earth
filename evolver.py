import heapq
import numpy as np
import uuid

from enum import Enum
from typing import Dict, Iterable

class CrossoverType(Enum):
    """A enum defining different crossover operations within a genetic algorthim."""
    UNIFORM = 1

class MutationType(Enum):
    """A enum defining different mutation operations for a genetic algorithm."""
    FLIP_BIT = 1 


class VectorEvolver():
    """A class for evolving a vector using a genetic algorithm."""

    def __init__(self, 
                 size: int, 
                 crossover_type: CrossoverType, 
                 mutation_type: MutationType):
        """Vector Evolver Ctor.

        Args:
            size: The size of the vector to evolve.
            crossover_type: The type of crossover operation used to produce new
                offspring.
            mutation_type: The type of mutation operation used to produce new
                offspring.
        """
        self._vec_size = size
        self.crossover_type = crossover_type
        self.mutation_type = mutation_type

        # Stores children of the current parents by their unique Ids.
        self._child_dict = {}
        
        # Min heap containing priorities and the corresponding uuids of 
        # children in the current generation.
        self._child_heap = []
        heapq.heapify(self._child_heap)

        self._generation = 0    
        self._generation_priorities = []

        # TODO(ameade): Consider parametrizing the number of parents and
        # allowing for off-spring to be created by multiple parents.
        self._num_parents = 2
        self._parents = [self.init_child() for i in range(self._num_parents)]

    
    # TODO(ameade) create a child class to allow typing enforcement.
    def add_child(self, child, priority: float) -> uuid.UUID:
        """Adds a child to the current generation with a given priority.
        
        Args:
            child: A child entry object.
            priority: A priority corresponding to the given child. A higher
                priority means the child is more likely to reproduce in the
                next generation.

        Returns:
            The UUID of the newly added child.

        """

        # UUIDs are used to track children.
        cid = uuid.uuid1()
        self._child_dict[cid] = child
        entry = [priority, cid]
        
        if len(self._child_heap) >= self._num_parents:
            # To prevent excessive memory usage only retain enough child to
            # select a new generation of parents.
            heapq.heapreplace(self._child_heap, entry)

        else:
            heapq.heappush(self._child_heap, entry)
        
        # Save priority for reporting stats later.
        self._generation_priorities.append(priority)
        return cid


    def spawn_child(self):
        """Creates a new child by applying mutations and crossovers to parents.

        Returns: 
            A new child object that has been evolved from its parents.
            
        """
        return self.mutate(self.crossover(self._parents[0], 
                                          self._parents[1]))   

    def update_parents(self):
        """Updates `self._parents by selecting the parents from the current
            generation of children."""
        
        # Since we are using a Min heap we select the parents based on those
        # with the highest priority and then recreate the heap.
        parents_cid = heapq.nlargest(self._num_parents, self._child_heap)
        self._parents = []
        for priority, pcid in parents_cid:
            self._parents.append(self._child_dict[pcid])
        
        # Reset Evolver.
        self._child_dict = {}
        self._child_heap = []
        heapq.heapify(self._child_heap)
        self._generation_priorities = []
        self._generation += 1

    def get_generation_stats(self) -> Dict[str, float]:
        """Gets a dictionary of statistics summarizing the current
        generation.
        
        Returns:
            A dictionary containing metric names and values.
        
        """
        return {
            'generation': self._generation,
            'mean': round(np.mean(self._generation_priorities), 2),
            'std': round(np.std(self._generation_priorities), 2)}

    def init_child(self):
        """Intializes a random new child vector.
        
        Returns:
            An np.ndarray.
            
        """
        return np.random.randint(low=0, high=1, size=self._vec_size)

    def crossover(self, p1, p2):
        """Performs a crossover operation combining two parents to produce
            a new child.
        
        Args:
            p1: The first parent vector to crossover.
            p2: The second parent vector to crossover.
                
        Returns:
            A new child vector containing a random combination of the two
            parents.

        """

        c = np.copy(p1)

        if self.crossover_type == CrossoverType.UNIFORM:
            crossover_bits = np.random.rand(self._vec_size) < 0.5 
            c[crossover_bits] = p2[crossover_bits]
        
        return c

    def mutate(self, p):
        """Mutates a vector to alter it from its original state.
        
        Args:
            p: The vector to mutate.
        
        Returns:
            The newly altered vector.
        """
        
        if self.mutation_type == MutationType.FLIP_BIT:
            mutation_bits = np.random.rand(self._vec_size) < (1 / self._vec_size)
            p[mutation_bits] = 1 - p[mutation_bits]

        return p


class MatrixEvolver(VectorEvolver):
    """A class to evolve matrices using genetic algorithims."""
    
    def __init__(self, 
                 sizes: Iterable[Iterable[int]],
                 crossover_type: CrossoverType,
                 mutation_type: MutationType):
        """Matrix Evolver Ctor.

        Args:
            sizes: An iterable containing the sizes of the matrices to evolve.
            crossover_type: The type of crossover operation used to produce new
                offspring.
            mutation_type: The type of mutation operation used to produce new
                offspring.
        """
        
        self._matrix_sizes = sizes
        self._matrix_params = [np.product(s) for s in self._matrix_sizes]
        self._total_params = np.sum(self._matrix_params)
        super().__init__(self._total_params, crossover_type, mutation_type)

    def vec_to_matrices(self, vec):
        """ Converts a vector to matrices whose size is defined by self.sizes.
        
        Args:
            vec: The vector to convert to matrices.
                
        Returns:
            The set of matrices reshaped from vec.

        """

        matrices = []
        idx = 0
        for i, s in enumerate(self._matrix_params):
            m = np.zeros(s)
            m[:] = vec[idx : idx + s]
            m = m.reshape(self._matrix_sizes[i])
            matrices.append(m)
            idx += s

        return matrices

    def matrices_to_vec(self, matrices):
        """Converts an iterable of matrices to a vector by reshaping them.
        
        Args:
            matrices: The matrices to flatten and concat to a single vector.
                
        Returns:
            The newly created vector from matrices.
        """

        vec = np.zeros(self._total_params)
        idx = 0

        for i, s in enumerate(self._matrix_params):
            vec[idx : idx + s] = matrices[i][:]
            idx += s

        return vec

    def spawn_child(self):
        """Creates a new set of child matrices by first spawning a vector and
        converting to matrix form.
        
        Returns:
            A new randomly generated set of child matrices.
            
        """

        return self.vec_to_matrices(super().spawn_child())

    def add_child(self, child, priority):
        """Appends a matrix to the set of tracked children with the provided
        priority. This is used to determine which children survive and produce
        offspring in each generation.
        
        Returns:
            A pointer to the entry containing the matrices and corresponding
            priority.
            
        """

        return super().add_child(self.matrices_to_vec(child), priority)
